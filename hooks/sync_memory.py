#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
"""
直近3リレーをSonnetで解析し、決定事項・タスク・トピックを一括でDBに記録するスクリプト。

Usage:
    python sync_memory.py <transcript_path>
"""
import json
import subprocess
import sys
from pathlib import Path

# 定数
ANALYSIS_MODEL = "sonnet"
MAX_USER_CONTENT_LENGTH = 1000
MAX_ASSISTANT_CONTENT_LENGTH = 2000

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.services.decision_service import add_decision
from src.services.task_service import add_task
from src.services.topic_service import add_topic

# record_log.pyから共通関数をインポート
from hooks.record_log import (
    read_transcript_tail,
    extract_text_content,
)
from hooks.llm_response_parser import extract_json_from_text
from hooks.parse_meta_tag import parse_meta_tag


def extract_relays_separately(entries: list[dict], n: int = 3) -> list[list[dict]]:
    """
    直近nリレーを個別のリストとして返す。

    1リレー = 人間のユーザー発言から次の人間発言の直前まで

    Args:
        entries: transcriptのエントリリスト
        n: 抽出するリレー数

    Returns:
        [[relay1], [relay2], [relay3]] のような形式
    """
    # システムエントリを除外
    filtered = [
        e for e in entries
        if e.get("type") not in ("file-history-snapshot", "system", "summary")
    ]

    # 人間のユーザー発言の位置を集める
    human_positions = [
        i for i, e in enumerate(filtered)
        if e.get("type") == "user" and "toolUseResult" not in e
    ]

    if not human_positions:
        return []

    # 直近n個のリレーを抽出
    relays = []
    positions_to_use = human_positions[-n:] if len(human_positions) >= n else human_positions

    for i, start_pos in enumerate(positions_to_use):
        # 次のリレーの開始位置を見つける
        if i + 1 < len(positions_to_use):
            end_pos = positions_to_use[i + 1]
        else:
            end_pos = len(filtered)

        relays.append(filtered[start_pos:end_pos])

    return relays


def extract_meta_from_relay(relay: list[dict]) -> dict | None:
    """
    リレーのassistantエントリからメタタグを抽出する。

    Returns:
        {"project_id": 2, "topic_id": 55} or None
    """
    # 後ろから探して最初に見つかったメタタグを返す
    for entry in reversed(relay):
        if entry.get("type") == "assistant":
            content = extract_text_content(entry)
            result = parse_meta_tag(content)
            if result and result.get("found"):
                return {
                    "project_id": result["project_id"],
                    "topic_id": result["topic_id"],
                }
    return None


def format_relay_for_analysis(relay: list[dict], meta: dict | None = None) -> str:
    """
    リレーを解析用にフォーマットする。

    Args:
        relay: リレーのエントリリスト
        meta: {"project_id": X, "topic_id": Y} or None
    """
    parts = []

    # メタ情報を先頭に追加
    if meta:
        parts.append(f"[project_id: {meta['project_id']}, topic_id: {meta['topic_id']}]")

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
                parts.append(f"User: {content[:MAX_USER_CONTENT_LENGTH]}")
        elif entry_type == "assistant":
            parts.append(f"Assistant: {content[:MAX_ASSISTANT_CONTENT_LENGTH]}")

    return "\n\n".join(parts)


def analyze_with_sonnet(relay_text: str) -> dict | None:
    """
    Sonnetで直近3リレーを解析し、決定事項・タスク・トピックを抽出する。

    Returns:
        {
            "decisions": [{"decision": "...", "reason": "...", "project_id": N, "topic_id": M}],
            "tasks": [{"title": "...", "description": "...", "project_id": N}],
            "topics": [{"title": "...", "description": "...", "project_id": N, "parent_topic_id": null}]
        }
    """
    if not relay_text:
        return None

    prompt = f"""以下の会話を解析して、決定事項・タスク・トピックを抽出してください。

【重要】各リレーには [project_id: X, topic_id: Y] が付与されています。
抽出した項目には、該当するリレーの project_id と topic_id を必ず含めてください。

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
   - 「〜する」「〜を確認する」など明確なアクションが求められるもの
   - 既に完了したタスクは含めない

3. **トピック（topics）**: 新しく立ち上がった議論テーマ
   - 新しい機能や改善案の議論が始まった場合
   - 既存のトピックの延長線上なら含めない

【出力形式】
「了解しました」などの前置きは不要です。JSON形式で直接出力してください。
何も抽出できなかった場合は空配列を返してください。
**各項目には必ず project_id と topic_id を含めてください（topicsは topic_id 不要）。**

```json
{{
  "decisions": [
    {{"decision": "確定した決定内容", "reason": "理由", "project_id": 2, "topic_id": 126}},
    {{"decision": "[議論中] 未決定の論点", "reason": "議論は出たが結論未定", "project_id": 2, "topic_id": 126}}
  ],
  "tasks": [
    {{"title": "タスク名", "description": "詳細説明", "project_id": 2}}
  ],
  "topics": [
    {{"title": "トピック名", "description": "説明", "project_id": 2, "parent_topic_id": null}}
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

        # JSON部分を抽出してパース
        data = extract_json_from_text(output)
        if data is None:
            print("Error: Failed to extract JSON from Sonnet output", file=sys.stderr)
            print(f"Output: {output}", file=sys.stderr)
            return None

        return data
    except Exception as e:
        print(f"Error calling Sonnet: {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: sync_memory.py <transcript_path>", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[1]

    # 1. transcriptから直近3リレーを個別に抽出
    entries = read_transcript_tail(transcript_path, max_lines=2000)
    if not entries:
        print("No entries found in transcript", file=sys.stderr)
        sys.exit(1)

    relays = extract_relays_separately(entries, n=3)
    if not relays:
        print("No relay found", file=sys.stderr)
        sys.exit(1)

    # 2. 各リレーからメタタグを抽出し、フォールバック用の最新メタ情報を取得
    fallback_meta = None
    relay_texts = []

    for relay in relays:
        meta = extract_meta_from_relay(relay)
        if meta:
            fallback_meta = meta  # 最新のメタ情報をフォールバック用に保持
        relay_text = format_relay_for_analysis(relay, meta)
        if relay_text:
            relay_texts.append(relay_text)

    if not relay_texts:
        print("Empty relay text", file=sys.stderr)
        sys.exit(1)

    if not fallback_meta:
        print("Error: No meta tag found in any relay", file=sys.stderr)
        sys.exit(1)

    # 3. 全リレーを結合して解析
    combined_text = "\n\n---\n\n".join(relay_texts)

    # 4. Sonnetで解析
    analysis_result = analyze_with_sonnet(combined_text)
    if not analysis_result:
        print("Error: Failed to analyze with Sonnet", file=sys.stderr)
        sys.exit(1)

    # 5. DBに記録（Sonnet出力のIDを優先、なければフォールバック）
    results = {
        "decisions": [],
        "tasks": [],
        "topics": [],
        "errors": [],
    }

    fallback_project_id = fallback_meta["project_id"]
    fallback_topic_id = fallback_meta["topic_id"]

    # 決定事項を記録
    for decision_data in analysis_result.get("decisions", []):
        if "decision" not in decision_data or "reason" not in decision_data:
            results["errors"].append(f"Invalid decision format: {decision_data}")
            continue

        # Sonnet出力のtopic_idを優先、なければフォールバック
        topic_id = decision_data.get("topic_id", fallback_topic_id)

        result = add_decision(
            decision=decision_data["decision"],
            reason=decision_data["reason"],
            topic_id=topic_id,
        )
        if "error" in result:
            results["errors"].append(f"Decision error: {result['error']}")
        else:
            results["decisions"].append(result.get("decision_id"))

    # タスクを記録
    for task_data in analysis_result.get("tasks", []):
        if "title" not in task_data or "description" not in task_data:
            results["errors"].append(f"Invalid task format: {task_data}")
            continue

        # Sonnet出力のproject_idを優先、なければフォールバック
        project_id = task_data.get("project_id", fallback_project_id)

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
        if "title" not in topic_data or "description" not in topic_data:
            results["errors"].append(f"Invalid topic format: {topic_data}")
            continue

        # Sonnet出力のproject_idを優先、なければフォールバック
        project_id = topic_data.get("project_id", fallback_project_id)

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
