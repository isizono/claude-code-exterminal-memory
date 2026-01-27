"""record_log.py のユニットテスト"""

import pytest
from record_log import extract_last_relay, extract_text_content, format_relay_for_summary


class TestExtractLastRelay:
    """extract_last_relay関数のテスト"""

    def test_single_relay(self):
        """1リレーのみの場合"""
        entries = [
            {"type": "user", "message": {"content": "質問"}},
            {"type": "assistant", "message": {"content": "回答"}},
        ]
        result = extract_last_relay(entries)
        assert len(result) == 2
        assert result[0]["type"] == "user"
        assert result[1]["type"] == "assistant"

    def test_multiple_relays(self):
        """複数リレーから最後の1つを抽出"""
        entries = [
            {"type": "user", "message": {"content": "最初の質問"}},
            {"type": "assistant", "message": {"content": "最初の回答"}},
            {"type": "user", "message": {"content": "2番目の質問"}},
            {"type": "assistant", "message": {"content": "2番目の回答"}},
        ]
        result = extract_last_relay(entries)
        assert len(result) == 2
        assert result[0]["message"]["content"] == "2番目の質問"
        assert result[1]["message"]["content"] == "2番目の回答"

    def test_multiple_relays_n2(self):
        """複数リレーから最後の2つを抽出"""
        entries = [
            {"type": "user", "message": {"content": "最初の質問"}},
            {"type": "assistant", "message": {"content": "最初の回答"}},
            {"type": "user", "message": {"content": "2番目の質問"}},
            {"type": "assistant", "message": {"content": "2番目の回答"}},
        ]
        result = extract_last_relay(entries, n=2)
        assert len(result) == 4
        assert result[0]["message"]["content"] == "最初の質問"

    def test_skip_tool_results(self):
        """toolUseResultはリレー境界として扱わない"""
        entries = [
            {"type": "user", "message": {"content": "質問"}},
            {"type": "assistant", "message": {"content": "ツール呼び出し"}},
            {"type": "user", "toolUseResult": True, "message": {"content": "結果"}},
            {"type": "assistant", "message": {"content": "最終回答"}},
        ]
        result = extract_last_relay(entries)
        assert len(result) == 4  # 全部同じリレー

    def test_skip_system_entries(self):
        """システムエントリはスキップ"""
        entries = [
            {"type": "user", "message": {"content": "質問"}},
            {"type": "system", "message": {"content": "システム"}},
            {"type": "assistant", "message": {"content": "回答"}},
        ]
        result = extract_last_relay(entries)
        assert len(result) == 2
        assert result[0]["type"] == "user"
        assert result[1]["type"] == "assistant"

    def test_skip_summary_entries(self):
        """summaryエントリはスキップ"""
        entries = [
            {"type": "summary", "message": {"content": "要約"}},
            {"type": "user", "message": {"content": "質問"}},
            {"type": "assistant", "message": {"content": "回答"}},
        ]
        result = extract_last_relay(entries)
        assert len(result) == 2

    def test_empty_entries(self):
        """空のエントリリスト"""
        result = extract_last_relay([])
        assert result == []

    def test_no_human_entries(self):
        """人間のユーザー発言がない場合"""
        entries = [
            {"type": "assistant", "message": {"content": "回答のみ"}},
        ]
        result = extract_last_relay(entries)
        assert result == []

    def test_n_larger_than_relays(self):
        """nがリレー数より大きい場合は全部返す"""
        entries = [
            {"type": "user", "message": {"content": "質問"}},
            {"type": "assistant", "message": {"content": "回答"}},
        ]
        result = extract_last_relay(entries, n=5)
        assert len(result) == 2


class TestExtractTextContent:
    """extract_text_content関数のテスト"""

    def test_string_content(self):
        """contentが文字列の場合"""
        entry = {"message": {"content": "テキスト"}}
        result = extract_text_content(entry)
        assert result == "テキスト"

    def test_text_blocks(self):
        """textブロックのリスト"""
        entry = {
            "message": {
                "content": [
                    {"type": "text", "text": "テキスト1"},
                    {"type": "text", "text": "テキスト2"},
                ]
            }
        }
        result = extract_text_content(entry)
        assert result == "テキスト1\nテキスト2"

    def test_tool_use_blocks(self):
        """tool_useブロックは[Tool: name]形式で出力"""
        entry = {
            "message": {
                "content": [
                    {"type": "text", "text": "テキスト"},
                    {"type": "tool_use", "name": "Read"},
                ]
            }
        }
        result = extract_text_content(entry)
        assert "[Tool: Read]" in result

    def test_empty_message(self):
        """messageが空の場合"""
        entry = {"message": {}}
        result = extract_text_content(entry)
        assert result == ""


class TestFormatRelayForSummary:
    """format_relay_for_summary関数のテスト"""

    def test_basic_format(self):
        """基本的なフォーマット"""
        relay = [
            {"type": "user", "message": {"content": "質問です"}},
            {"type": "assistant", "message": {"content": "回答です"}},
        ]
        result = format_relay_for_summary(relay)
        assert "User: 質問です" in result
        assert "Assistant: 回答です" in result

    def test_tool_result_abbreviated(self):
        """toolUseResultは[Tool Result]に省略"""
        relay = [
            {"type": "user", "message": {"content": "質問"}},
            {"type": "assistant", "message": {"content": "ツール呼び出し"}},
            {"type": "user", "toolUseResult": True, "message": {"content": "長い結果..."}},
            {"type": "assistant", "message": {"content": "回答"}},
        ]
        result = format_relay_for_summary(relay)
        assert "[Tool Result]" in result
        assert "長い結果" not in result

    def test_long_user_message_truncated(self):
        """長いユーザーメッセージは500文字で切り詰め"""
        long_text = "あ" * 1000
        relay = [
            {"type": "user", "message": {"content": long_text}},
        ]
        result = format_relay_for_summary(relay)
        # User: + 500文字
        assert len(result) < 600

    def test_long_assistant_message_truncated(self):
        """長いアシスタントメッセージは1000文字で切り詰め"""
        long_text = "あ" * 2000
        relay = [
            {"type": "assistant", "message": {"content": long_text}},
        ]
        result = format_relay_for_summary(relay)
        # Assistant: + 1000文字
        assert len(result) < 1100

    def test_empty_relay(self):
        """空のリレー"""
        result = format_relay_for_summary([])
        assert result == ""
