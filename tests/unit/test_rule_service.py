"""rule_serviceのユニットテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.services.rule_service import add_rule, list_rules, update_rule


@pytest.fixture
def temp_db():
    """テスト用の一時的なデータベースを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        os.environ["DISCUSSION_DB_PATH"] = db_path
        init_database()
        yield db_path
        if "DISCUSSION_DB_PATH" in os.environ:
            del os.environ["DISCUSSION_DB_PATH"]


class TestAddRule:
    """add_ruleのテスト"""

    def test_add_rule_success(self, temp_db):
        """ルールが正常に追加される"""
        result = add_rule("テストルール")

        assert "error" not in result
        assert result["rule_id"] is not None
        assert result["content"] == "テストルール"
        assert result["active"] == 1
        assert result["created_at"] is not None

    def test_add_rule_empty_content(self, temp_db):
        """空文字のcontentでバリデーションエラーになる"""
        result = add_rule("")

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "content" in result["error"]["message"]

    def test_add_rule_whitespace_only(self, temp_db):
        """空白のみのcontentでバリデーションエラーになる"""
        result = add_rule("   ")

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"

    def test_add_multiple_rules(self, temp_db):
        """複数のルールを追加できる"""
        result1 = add_rule("ルール1")
        result2 = add_rule("ルール2")

        assert "error" not in result1
        assert "error" not in result2
        assert result1["rule_id"] != result2["rule_id"]


class TestListRules:
    """list_rulesのテスト"""

    def test_list_rules_with_initial_data(self, temp_db):
        """マイグレーションで投入された初期データが含まれる"""
        result = list_rules()

        assert "error" not in result
        assert result["total_count"] >= 1
        # 初期データの内容を確認
        contents = [r["content"] for r in result["rules"]]
        assert any("IDを指示語代わりにしない" in c for c in contents)

    def test_list_rules_after_add(self, temp_db):
        """追加したルールが一覧に含まれる"""
        add_rule("新しいルール")

        result = list_rules()

        assert "error" not in result
        contents = [r["content"] for r in result["rules"]]
        assert "新しいルール" in contents

    def test_list_rules_order_by_id(self, temp_db):
        """ルールがID順にソートされている"""
        add_rule("ルールA")
        add_rule("ルールB")

        result = list_rules()

        assert "error" not in result
        ids = [r["rule_id"] for r in result["rules"]]
        assert ids == sorted(ids)


class TestUpdateRule:
    """update_ruleのテスト"""

    def test_update_content(self, temp_db):
        """contentを更新できる"""
        created = add_rule("元のルール")
        rule_id = created["rule_id"]

        result = update_rule(rule_id, content="更新後のルール")

        assert "error" not in result
        assert result["rule_id"] == rule_id
        assert result["content"] == "更新後のルール"
        assert result["active"] == 1

    def test_update_active_to_zero(self, temp_db):
        """active=0で無効化できる"""
        created = add_rule("無効化するルール")
        rule_id = created["rule_id"]

        result = update_rule(rule_id, active=0)

        assert "error" not in result
        assert result["rule_id"] == rule_id
        assert result["active"] == 0

    def test_update_active_to_one(self, temp_db):
        """active=1で再有効化できる"""
        created = add_rule("再有効化するルール")
        rule_id = created["rule_id"]
        update_rule(rule_id, active=0)

        result = update_rule(rule_id, active=1)

        assert "error" not in result
        assert result["active"] == 1

    def test_update_both_content_and_active(self, temp_db):
        """contentとactiveを同時に更新できる"""
        created = add_rule("元のルール")
        rule_id = created["rule_id"]

        result = update_rule(rule_id, content="新しいルール", active=0)

        assert "error" not in result
        assert result["content"] == "新しいルール"
        assert result["active"] == 0

    def test_update_no_params(self, temp_db):
        """content/active両方未指定でバリデーションエラーになる"""
        result = update_rule(1)

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "At least one" in result["error"]["message"]

    def test_update_not_found(self, temp_db):
        """存在しないIDでNOT_FOUNDエラーになる"""
        result = update_rule(9999, content="存在しないルール")

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"
        assert "9999" in result["error"]["message"]

    def test_update_empty_content(self, temp_db):
        """空文字のcontentでバリデーションエラーになる"""
        created = add_rule("元のルール")
        rule_id = created["rule_id"]

        result = update_rule(rule_id, content="")

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"

    def test_update_invalid_active(self, temp_db):
        """active=2のような無効値でバリデーションエラーになる"""
        created = add_rule("元のルール")
        rule_id = created["rule_id"]

        result = update_rule(rule_id, active=2)

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "active must be 0 or 1" in result["error"]["message"]
