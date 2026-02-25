#!/usr/bin/env python3
"""
直近Nターン分のassistantエントリにadd_decision/add_topicの呼び出しがあるかチェック。
stop_nudge_record.shから呼び出される。

Usage:
    python check_recent_recording.py <transcript_path> [turns=3]

Returns:
    "true" if add_decision or add_topic was called in recent turns, "false" otherwise
"""
import json
import sys
from pathlib import Path


TARGET_TOOLS = [
    "mcp__plugin_claude-code-memory_cc-memory__add_decision",
    "mcp__plugin_claude-code-memory_cc-memory__add_topic",
]


def get_recent_assistant_entries(transcript_path: str, n: int) -> list[dict]:
    """transcriptから直近N件のassistantエントリを取得する"""
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

    return entries[-n:] if entries else []


def has_recording_calls(entries: list[dict]) -> bool:
    """entriesにadd_decision/add_topicのツール呼び出しがあるかチェック"""
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
            if block.get("name", "") in TARGET_TOOLS:
                return True

    return False


def main():
    if len(sys.argv) < 2:
        print("false")
        sys.exit(0)

    transcript_path = sys.argv[1]
    turns = 3
    if len(sys.argv) >= 3:
        try:
            turns = int(sys.argv[2])
        except ValueError:
            pass

    entries = get_recent_assistant_entries(transcript_path, turns)
    print("true" if has_recording_calls(entries) else "false")


if __name__ == "__main__":
    main()
