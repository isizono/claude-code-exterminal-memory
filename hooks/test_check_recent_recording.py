#!/usr/bin/env python3
"""check_recent_recording.py のテスト"""
import json
import tempfile
from pathlib import Path

from check_recent_recording import get_recent_assistant_entries, has_recording_calls


def _write_transcript(lines: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def _make_assistant_entry(tool_calls: list[str] | None = None, text: str = "") -> dict:
    content = []
    if text:
        content.append({"type": "text", "text": text})
    if tool_calls:
        for tool in tool_calls:
            content.append({"type": "tool_use", "name": tool, "input": {}})
    return {"type": "assistant", "message": {"content": content}}


def _make_user_entry(text: str = "hello") -> dict:
    return {"type": "human", "message": {"content": [{"type": "text", "text": text}]}}


class TestGetRecentAssistantEntries:
    def test_empty_file(self, tmp_path):
        path = tmp_path / "transcript.jsonl"
        path.write_text("")
        assert get_recent_assistant_entries(str(path), 3) == []

    def test_nonexistent_file(self, tmp_path):
        path = tmp_path / "nonexistent.jsonl"
        assert get_recent_assistant_entries(str(path), 3) == []

    def test_no_assistant_entries(self, tmp_path):
        path = tmp_path / "transcript.jsonl"
        lines = [_make_user_entry("only user entries")]
        _write_transcript(lines, path)
        result = get_recent_assistant_entries(str(path), 3)
        assert result == []

    def test_returns_last_n_entries(self, tmp_path):
        path = tmp_path / "transcript.jsonl"
        entries = [
            _make_assistant_entry(text=f"msg{i}") for i in range(5)
        ]
        # user entries between
        lines = []
        for e in entries:
            lines.append(_make_user_entry())
            lines.append(e)
        _write_transcript(lines, path)

        result = get_recent_assistant_entries(str(path), 3)
        assert len(result) == 3
        # last 3 assistant entries
        assert result[0]["message"]["content"][0]["text"] == "msg2"
        assert result[1]["message"]["content"][0]["text"] == "msg3"
        assert result[2]["message"]["content"][0]["text"] == "msg4"


class TestHasRecordingCalls:
    def test_no_tool_calls(self):
        entries = [_make_assistant_entry(text="hello")]
        assert has_recording_calls(entries) is False

    def test_unrelated_tool_calls(self):
        entries = [_make_assistant_entry(tool_calls=["mcp__plugin_claude-code-memory_cc-memory__search"])]
        assert has_recording_calls(entries) is False

    def test_add_decision_detected(self):
        entries = [_make_assistant_entry(tool_calls=["mcp__plugin_claude-code-memory_cc-memory__add_decision"])]
        assert has_recording_calls(entries) is True

    def test_add_topic_detected(self):
        entries = [_make_assistant_entry(tool_calls=["mcp__plugin_claude-code-memory_cc-memory__add_topic"])]
        assert has_recording_calls(entries) is True

    def test_mixed_entries(self):
        entries = [
            _make_assistant_entry(text="thinking..."),
            _make_assistant_entry(tool_calls=["mcp__plugin_claude-code-memory_cc-memory__search"]),
            _make_assistant_entry(tool_calls=["mcp__plugin_claude-code-memory_cc-memory__add_decision"]),
        ]
        assert has_recording_calls(entries) is True

    def test_string_content(self):
        entry = {"type": "assistant", "message": {"content": "just a string"}}
        assert has_recording_calls([entry]) is False
