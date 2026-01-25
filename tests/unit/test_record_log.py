"""record_log.py のユニットテスト"""
import pytest
import sys
from pathlib import Path

# hooks ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "hooks"))

from record_log import extract_last_relay


def make_user_entry(text: str) -> dict:
    """ユーザーエントリを作成"""
    return {
        "type": "user",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def make_assistant_entry(text: str) -> dict:
    """アシスタントエントリを作成"""
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def make_system_entry() -> dict:
    """システムエントリを作成"""
    return {"type": "system", "message": {"content": "system message"}}


def make_tool_result_entry() -> dict:
    """ツール結果エントリを作成（ユーザーだがリレー開始ではない）"""
    return {
        "type": "user",
        "toolUseResult": {"result": "some result"},
        "message": {"content": "tool result"},
    }


class TestExtractLastRelay:
    """extract_last_relay のテスト"""

    def test_empty_entries(self):
        """空のエントリリストを渡すと空リストを返す"""
        result = extract_last_relay([])
        assert result == []

    def test_no_human_entries(self):
        """人間のユーザー発言がない場合は空リストを返す"""
        entries = [make_assistant_entry("hello"), make_system_entry()]
        result = extract_last_relay(entries)
        assert result == []

    def test_single_relay(self):
        """1リレーのみの場合"""
        entries = [
            make_user_entry("user message"),
            make_assistant_entry("assistant response"),
        ]
        result = extract_last_relay(entries, n=1)
        assert len(result) == 2
        assert result[0]["message"]["content"][0]["text"] == "user message"

    def test_extract_n_relays(self):
        """n個のリレーを抽出"""
        entries = [
            make_user_entry("user1"),
            make_assistant_entry("assistant1"),
            make_user_entry("user2"),
            make_assistant_entry("assistant2"),
            make_user_entry("user3"),
            make_assistant_entry("assistant3"),
        ]
        result = extract_last_relay(entries, n=2)
        # 最後の2リレー（user2から開始）
        assert len(result) == 4
        assert result[0]["message"]["content"][0]["text"] == "user2"

    def test_fewer_relays_than_requested(self):
        """要求されたリレー数より少ない場合は利用可能な全リレーを返す"""
        entries = [
            make_system_entry(),  # これは除外される
            make_user_entry("user1"),
            make_assistant_entry("assistant1"),
            make_user_entry("user2"),
            make_assistant_entry("assistant2"),
        ]
        # 3リレー要求したが2リレーしかない
        result = extract_last_relay(entries, n=3)
        # 最初のuser発言から開始（systemは含まない）
        assert len(result) == 4
        assert result[0]["message"]["content"][0]["text"] == "user1"

    def test_system_entries_excluded(self):
        """システムエントリは除外される"""
        entries = [
            make_system_entry(),
            make_user_entry("user1"),
            {"type": "file-history-snapshot", "data": {}},
            make_assistant_entry("assistant1"),
            {"type": "summary", "content": "summary"},
        ]
        result = extract_last_relay(entries, n=1)
        # system, file-history-snapshot, summaryは除外
        assert len(result) == 2
        assert all(e.get("type") not in ("system", "file-history-snapshot", "summary") for e in result)

    def test_tool_result_not_relay_start(self):
        """toolUseResultを持つuserエントリはリレー開始とみなさない"""
        entries = [
            make_user_entry("user1"),
            make_assistant_entry("assistant1"),
            make_tool_result_entry(),  # これはリレー開始ではない
            make_assistant_entry("assistant2"),
            make_user_entry("user2"),
            make_assistant_entry("assistant3"),
        ]
        result = extract_last_relay(entries, n=1)
        # 最後のリレーはuser2から
        assert result[0]["message"]["content"][0]["text"] == "user2"

    def test_only_one_relay_when_requesting_three(self):
        """1リレーしかないのに3リレー要求した場合"""
        entries = [
            make_system_entry(),
            make_user_entry("only user"),
            make_assistant_entry("only assistant"),
        ]
        result = extract_last_relay(entries, n=3)
        # 利用可能な1リレーのみ返す（systemは除外）
        assert len(result) == 2
        assert result[0]["message"]["content"][0]["text"] == "only user"
