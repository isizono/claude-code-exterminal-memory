"""update_subjectのユニットテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.services.subject_service import add_subject, update_subject


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


@pytest.fixture
def test_subject(temp_db):
    """テスト用サブジェクトを作成する"""
    result = add_subject(name="original-name", description="Original description")
    return result


# ========================================
# 正常系テスト
# ========================================


class TestUpdateSubjectSuccess:
    """update_subjectの正常系テスト"""

    def test_update_name(self, test_subject):
        """名前のみ変更できる"""
        result = update_subject(test_subject["subject_id"], name="new-name")

        assert "error" not in result
        assert result["name"] == "new-name"
        assert result["description"] == "Original description"

    def test_update_description(self, test_subject):
        """説明のみ変更できる"""
        result = update_subject(test_subject["subject_id"], description="New description")

        assert "error" not in result
        assert result["description"] == "New description"
        assert result["name"] == "original-name"


# ========================================
# 異常系テスト
# ========================================


class TestUpdateSubjectError:
    """update_subjectの異常系テスト"""

    def test_all_none_returns_validation_error(self, test_subject):
        """全パラメータがNoneだとVALIDATION_ERRORになる"""
        result = update_subject(test_subject["subject_id"])

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"

    def test_not_found(self, temp_db):
        """存在しないサブジェクトIDでNOT_FOUNDになる"""
        result = update_subject(9999, name="new-name")

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"

    def test_empty_name(self, test_subject):
        """空文字のnameでVALIDATION_ERRORになる"""
        result = update_subject(test_subject["subject_id"], name="")

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "name" in result["error"]["message"]

    def test_whitespace_name(self, test_subject):
        """空白のみのnameでVALIDATION_ERRORになる"""
        result = update_subject(test_subject["subject_id"], name="   ")

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "name" in result["error"]["message"]

    def test_empty_description(self, test_subject):
        """空文字のdescriptionでVALIDATION_ERRORになる"""
        result = update_subject(test_subject["subject_id"], description="")

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "description" in result["error"]["message"]

    def test_duplicate_name(self, temp_db):
        """名前重複時にCONSTRAINT_VIOLATIONになる"""
        add_subject(name="subject-a", description="Subject A")
        subject_b = add_subject(name="subject-b", description="Subject B")

        result = update_subject(subject_b["subject_id"], name="subject-a")

        assert "error" in result
        assert result["error"]["code"] == "CONSTRAINT_VIOLATION"
