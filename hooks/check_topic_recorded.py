#!/usr/bin/env python3
"""
指定トピックに対してadd_decisionまたはadd_logが呼び出されたかチェックするスクリプト。
Stopフックからトピック変更時に呼び出される。

transcriptをパースして、該当トピックへのツール呼び出しを検知する。

Usage:
    python check_topic_recorded.py <topic_id> <transcript_path>

Returns:
    "true" if add_decision or add_log was called for the topic, "false" otherwise
"""
import json
import sys
from pathlib import Path


def get_all_assistant_entries(transcript_path: str) -> list[dict]:
    """transcriptからすべてのassistantエントリを取得する"""
    path = Path(transcript_path).expanduser()
    if not path.exists():
        return []

    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    return entries


def find_tool_calls_for_topic(entries: list[dict], topic_id: int) -> bool:
    """
    entriesからadd_decision/add_logのツール呼び出しを探し、
    指定topic_idに対する呼び出しがあるかチェックする。
    """
    target_tools = [
        "mcp__plugin_claude-code-memory_claude-code-memory__add_decision",
        "mcp__plugin_claude-code-memory_claude-code-memory__add_log",
    ]

    for entry in entries:
        message = entry.get("message", {})
        content = message.get("content", [])

        if isinstance(content, str):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            if block.get("type") != "tool_use":
                continue

            tool_name = block.get("name", "")
            if tool_name not in target_tools:
                continue

            # ツール呼び出しの引数をチェック
            tool_input = block.get("input", {})
            called_topic_id = tool_input.get("topic_id")

            if called_topic_id is not None:
                try:
                    if int(called_topic_id) == topic_id:
                        return True
                except (ValueError, TypeError):
                    continue

    return False


def main():
    if len(sys.argv) < 3:
        print("false")
        sys.exit(0)

    try:
        topic_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid topic_id: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[2]
    entries = get_all_assistant_entries(transcript_path)

    if find_tool_calls_for_topic(entries, topic_id):
        print("true")
    else:
        print("false")


if __name__ == "__main__":
    main()
