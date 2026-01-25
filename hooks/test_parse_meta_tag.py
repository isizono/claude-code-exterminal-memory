"""parse_meta_tag.py のユニットテスト"""

import pytest
from parse_meta_tag import parse_meta_tag, extract_text_from_entry


class TestParseMetaTag:
    """parse_meta_tag関数のテスト"""

    def test_valid_meta_tag(self):
        """正常なメタタグをパースできる"""
        text = '<!-- [meta] project: claude-code-exterminal-memory (id: 2) | topic: Stopフック実装 (id: 55) -->'
        result = parse_meta_tag(text)
        assert result == {"found": True, "project_id": 2, "topic_id": 55}

    def test_meta_tag_with_surrounding_text(self):
        """前後にテキストがあってもパースできる"""
        text = """これは応答の本文です。

<!-- [meta] project: テストプロジェクト (id: 10) | topic: テストトピック (id: 100) -->"""
        result = parse_meta_tag(text)
        assert result == {"found": True, "project_id": 10, "topic_id": 100}

    def test_meta_tag_with_japanese(self):
        """日本語のプロジェクト名・トピック名をパースできる"""
        text = '<!-- [meta] project: 日本語プロジェクト (id: 5) | topic: 日本語トピック (id: 99) -->'
        result = parse_meta_tag(text)
        assert result == {"found": True, "project_id": 5, "topic_id": 99}

    def test_no_meta_tag(self):
        """メタタグがない場合はNoneを返す"""
        text = "これはただのテキストです。メタタグはありません。"
        result = parse_meta_tag(text)
        assert result is None

    def test_empty_text(self):
        """空文字列の場合はNoneを返す"""
        result = parse_meta_tag("")
        assert result is None

    def test_malformed_meta_tag(self):
        """不正なフォーマットはNoneを返す"""
        # idがない
        text = '<!-- [meta] project: test | topic: test -->'
        result = parse_meta_tag(text)
        assert result is None

    def test_large_ids(self):
        """大きなID値もパースできる"""
        text = '<!-- [meta] project: big (id: 999999) | topic: numbers (id: 888888) -->'
        result = parse_meta_tag(text)
        assert result == {"found": True, "project_id": 999999, "topic_id": 888888}


class TestExtractTextFromEntry:
    """extract_text_from_entry関数のテスト"""

    def test_string_content(self):
        """contentが文字列の場合"""
        entry = {"message": {"content": "テキスト内容"}}
        result = extract_text_from_entry(entry)
        assert result == "テキスト内容"

    def test_list_content_with_text_blocks(self):
        """contentがtextブロックのリストの場合"""
        entry = {
            "message": {
                "content": [
                    {"type": "text", "text": "最初のテキスト"},
                    {"type": "text", "text": "2番目のテキスト"},
                ]
            }
        }
        result = extract_text_from_entry(entry)
        assert result == "最初のテキスト\n2番目のテキスト"

    def test_list_content_with_mixed_blocks(self):
        """contentにtool_useブロックが混在する場合"""
        entry = {
            "message": {
                "content": [
                    {"type": "text", "text": "テキスト"},
                    {"type": "tool_use", "name": "Read"},
                ]
            }
        }
        result = extract_text_from_entry(entry)
        # tool_useは無視される（この関数ではtextのみ抽出）
        assert result == "テキスト"

    def test_empty_message(self):
        """messageが空の場合"""
        entry = {"message": {}}
        result = extract_text_from_entry(entry)
        assert result == ""

    def test_no_message(self):
        """messageがない場合"""
        entry = {}
        result = extract_text_from_entry(entry)
        assert result == ""

    def test_list_of_strings(self):
        """contentが文字列のリストの場合"""
        entry = {"message": {"content": ["文字列1", "文字列2"]}}
        result = extract_text_from_entry(entry)
        assert result == "文字列1\n文字列2"
