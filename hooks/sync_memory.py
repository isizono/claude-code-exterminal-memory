#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
直近3リレーをSonnetで解析し、決定事項・タスク・トピックを一括でDBに記録するスクリプト。

Usage:
    python sync_memory.py <transcript_path> <topic_id>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# モデル定数
ANALYSIS_MODEL = "sonnet"

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.services.decision_service import add_decision
from src.services.task_service import add_task
from src.services.topic_service import add_topic

# record_log.pyから共通関数をインポート
from hooks.record_log import (
    read_transcript_tail,
    extract_last_relay,
    extract_text_content,
)


def format_relay_for_analysis(relay: list[dict]) -> str:
    """リレーを解析用にフォーマットする"""
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
                parts.append(f"User: {content[:1000]}")
        elif entry_type == "assistant":
            parts.append(f"Assistant: {content[:2000]}")

    return "\n\n".join(parts)


def analyze_with_sonnet(relay_text: str) -> dict | None:
    """
    Sonnetで直近3リレーを解析し、決定事項・タスク・トピックを抽出する。

    Returns:
        {
            "decisions": [{"decision": "...", "reason": "..."}],
            "tasks": [{"title": "...", "description": "..."}],
            "topics": [{"title": "...", "description": "...", "parent_topic_id": null}]
        }
    """
    if not relay_text:
        return None

    prompt = f"""以下の会話を解析して、決定事項・タスク・トピックを抽出してください。

【抽出ルール】
1. **決定事項（decisions）**: 確定した内容と未決定の論点の両方を記録

   **確定した決定事項:**
   - 「これでいこう」「OK」「了解」など明確な合意があったもの
   - decisionにそのまま記載

   **未決定の論点（重要！）:**
   - 議論に出たが結論が出ていない論点
   - 「〜かも」「〜という案もある」「〜どうしようかな」
   - 提案されたが承認/却下がまだのアイデア
   - **decisionの先頭に `[議論中]` または `[未完]` をつける**
   - 例: "[議論中] JSONパースの正規表現をどう改善するか"

2. **タスク（tasks）**: 今後やるべき具体的なタスク
   - 実装、調査、設計、議論、レビューなど種類は問わない
   - 「〜する」「〜を確認する」など明確なアクションがあるもの
   - 既に完了したタスクは含めない

3. **トピック（topics）**: 新しく立ち上がった議論テーマ
   - 新しい機能や改善案の議論が始まった場合
   - 既存のトピックの延長線上なら含めない

【出力形式】
必ずJSON形式で出力してください。何も抽出できなかった場合は空配列を返してください。

```json
{{
  "decisions": [
    {{"decision": "確定した決定内容", "reason": "理由"}},
    {{"decision": "[議論中] 未決定の論点", "reason": "議論は出たが結論未定"}}
  ],
  "tasks": [
    {{"title": "タスク名", "description": "詳細説明"}}
  ],
  "topics": [
    {{"title": "トピック名", "description": "説明", "parent_topic_id": null}}
  ]
}}
```

【会話内容】
{relay_text}"""

    try:
        result = subprocess.run(
            ["claude", "--model", ANALYSIS_MODEL, "--setting-sources", "", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"Error: claude command failed with exit code {result.returncode}", file=sys.stderr)
            print(f"stderr: {result.stderr}", file=sys.stderr)
            return None

        output = result.stdout.strip()

        # JSON部分を抽出（```json ... ``` で囲まれている場合）
        json_match = output
        if "```json" in output:
            match = re.search(r'```json\s*(\{.*?\})\s*```', output, re.DOTALL)
            if match:
                json_match = match.group(1)

        # JSONをパース
        data = json.loads(json_match)
        return data

    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON from Sonnet output: {e}", file=sys.stderr)
        print(f"Output: {output}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error calling Sonnet: {e}", file=sys.stderr)
        return None


def parse_meta_tag_from_transcript(transcript_path: str) -> dict | None:
    """
    transcriptからメタタグを取得してproject_idを抽出する。

    Returns:
        {"found": True, "project_id": 2, "topic_id": 55}
        or
        {"found": False}
    """
    try:
        result = subprocess.run(
            ["python3", str(project_root / "hooks" / "parse_meta_tag.py"), transcript_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            return {"found": False}
    except Exception as e:
        print(f"Error parsing meta tag: {e}", file=sys.stderr)
        return {"found": False}


def main():
    if len(sys.argv) < 3:
        print("Usage: sync_memory.py <transcript_path> <topic_id>", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[1]
    try:
        current_topic_id = int(sys.argv[2])
    except ValueError:
        print("Invalid topic_id", file=sys.stderr)
        sys.exit(1)

    # 1. transcriptから直近3リレーを抽出
    entries = read_transcript_tail(transcript_path, max_lines=2000)
    if not entries:
        print("No entries found in transcript", file=sys.stderr)
        sys.exit(1)

    relay = extract_last_relay(entries, n=3)
    if not relay:
        print("No relay found", file=sys.stderr)
        sys.exit(1)

    # 2. メタタグからproject_idを取得
    meta_result = parse_meta_tag_from_transcript(transcript_path)
    if not meta_result.get("found"):
        print("Error: Meta tag not found in transcript", file=sys.stderr)
        sys.exit(1)

    project_id = meta_result["project_id"]

    # 3. 解析用にフォーマット
    relay_text = format_relay_for_analysis(relay)
    if not relay_text:
        print("Empty relay text", file=sys.stderr)
        sys.exit(1)

    # 4. Sonnetで解析
    analysis_result = analyze_with_sonnet(relay_text)
    if not analysis_result:
        print("Error: Failed to analyze with Sonnet", file=sys.stderr)
        sys.exit(1)

    # 5. DBに記録
    results = {
        "decisions": [],
        "tasks": [],
        "topics": [],
        "errors": [],
    }

    # 決定事項を記録
    for decision_data in analysis_result.get("decisions", []):
        result = add_decision(
            decision=decision_data["decision"],
            reason=decision_data["reason"],
            topic_id=current_topic_id,
        )
        if "error" in result:
            results["errors"].append(f"Decision error: {result['error']}")
        else:
            results["decisions"].append(result.get("decision_id"))

    # タスクを記録
    for task_data in analysis_result.get("tasks", []):
        result = add_task(
            project_id=project_id,
            title=task_data["title"],
            description=task_data["description"],
        )
        if "error" in result:
            results["errors"].append(f"Task error: {result['error']}")
        else:
            results["tasks"].append(result.get("task_id"))

    # トピックを記録
    for topic_data in analysis_result.get("topics", []):
        result = add_topic(
            project_id=project_id,
            title=topic_data["title"],
            description=topic_data["description"],
            parent_topic_id=topic_data.get("parent_topic_id"),
        )
        if "error" in result:
            results["errors"].append(f"Topic error: {result['error']}")
        else:
            results["topics"].append(result.get("topic_id"))

    # 6. 結果を出力
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # エラーがあった場合は終了コード1
    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
