#!/usr/bin/env python3
"""
Stopフックからバックグラウンドで呼び出されるログ記録スクリプト。
transcriptから直近1リレーを抽出し、Haikuで要約してDBに保存する。

Usage:
    python record_log.py <transcript_path> <topic_id>
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.services.discussion_log_service import add_log


def read_transcript_tail(transcript_path: str, max_lines: int = 1000) -> list[dict]:
    """
    transcriptファイルの末尾から指定行数を読み込む。
    大きなファイルでもメモリ効率よく処理する。
    """
    entries = []
    path = Path(transcript_path).expanduser()

    if not path.exists():
        return []

    # tailコマンドで末尾を取得（macOS/Linux互換）
    try:
        result = subprocess.run(
            ["tail", "-n", str(max_lines), str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.strip().split("\n")
    except Exception:
        # フォールバック: ファイル全体を読む
        with open(path) as f:
            lines = f.readlines()[-max_lines:]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries


def extract_last_relay(entries: list[dict]) -> list[dict]:
    """
    直近1リレーを抽出する。

    1リレーの定義:
    - 人間のユーザー発言（type=user, toolUseResultなし）から開始
    - 次の人間のユーザー発言の直前まで
    """
    relay = []
    found_human = False

    for entry in reversed(entries):
        entry_type = entry.get("type", "")

        # システムエントリはスキップ
        if entry_type in ("file-history-snapshot", "system", "summary"):
            continue

        # 人間のユーザー発言を判定
        is_human = entry_type == "user" and "toolUseResult" not in entry

        if is_human:
            if found_human:
                # 前のリレーに到達したので終了
                break
            found_human = True

        relay.insert(0, entry)

    return relay


def extract_text_content(entry: dict) -> str:
    """エントリからテキスト内容を抽出する"""
    message = entry.get("message", {})
    content = message.get("content", [])

    if isinstance(content, str):
        return content

    texts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                texts.append(f"[Tool: {block.get('name', 'unknown')}]")
        elif isinstance(block, str):
            texts.append(block)

    return "\n".join(texts)


def format_relay_for_summary(relay: list[dict]) -> str:
    """リレーを要約用にフォーマットする"""
    parts = []

    for entry in relay:
        entry_type = entry.get("type", "")
        content = extract_text_content(entry)

        if not content:
            continue

        if entry_type == "user":
            if "toolUseResult" in entry:
                # ツール結果は省略
                parts.append("[Tool Result]")
            else:
                parts.append(f"User: {content[:500]}")  # 長すぎる場合は切り詰め
        elif entry_type == "assistant":
            parts.append(f"Assistant: {content[:1000]}")

    return "\n\n".join(parts)


def summarize_with_haiku(relay_text: str) -> Optional[str]:
    """Haikuで要約する"""
    if not relay_text:
        return None

    prompt = f"""以下の会話を1〜2文で要約してください。
形式: 「ユーザー: 〇〇について質問/依頼 → AI: △△と回答/実行」

{relay_text}"""

    try:
        result = subprocess.run(
            ["claude", "--model", "haiku", "--setting-sources", "", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception as e:
        print(f"Error calling Haiku: {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 3:
        print("Usage: record_log.py <transcript_path> <topic_id>", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[1]
    try:
        topic_id = int(sys.argv[2])
    except ValueError:
        print("Invalid topic_id", file=sys.stderr)
        sys.exit(1)

    # 1. transcriptから直近1リレーを抽出
    entries = read_transcript_tail(transcript_path)
    if not entries:
        print("No entries found in transcript", file=sys.stderr)
        sys.exit(1)

    relay = extract_last_relay(entries)
    if not relay:
        print("No relay found", file=sys.stderr)
        sys.exit(1)

    # 2. 要約用にフォーマット
    relay_text = format_relay_for_summary(relay)
    if not relay_text:
        print("Empty relay text", file=sys.stderr)
        sys.exit(1)

    # 3. Haikuで要約
    summary = summarize_with_haiku(relay_text)
    if not summary:
        # 要約に失敗した場合は元のテキストを短縮して保存
        summary = relay_text[:500] + "..." if len(relay_text) > 500 else relay_text

    # 4. DBに保存
    result = add_log(topic_id, summary)
    if "error" in result:
        print(f"Error saving log: {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"Log saved: {result.get('log_id')}")


if __name__ == "__main__":
    main()
