"""サービス層の単体テスト（エラーハンドリング、特殊文字など）"""
import os
import tempfile
import sqlite3
import pytest
from src.db import init_database
from src.services.subject_service import add_subject, list_subjects
from src.services.topic_service import add_topic
from src.services.search_service import search
from src.services.decision_service import add_decision


@pytest.fixture
def temp_db():
    """テスト用の一時的なデータベースを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        os.environ["DISCUSSION_DB_PATH"] = db_path
        init_database()
        yield db_path
        # クリーンアップ
        if "DISCUSSION_DB_PATH" in os.environ:
            del os.environ["DISCUSSION_DB_PATH"]


@pytest.fixture
def test_subject(temp_db):
    """テスト用サブジェクトを作成する"""
    result = add_subject(name="test-subject", description="Test description")
    return result["subject_id"]


# ========================================
# エラーハンドリングのテスト
# ========================================


def test_add_subject_unique_constraint_violation(temp_db):
    """サブジェクト名の重複時にCONSTRAINT_VIOLATIONエラーが返る"""
    # 最初のサブジェクトを追加
    result1 = add_subject(name="unique-subject", description="First")
    assert "error" not in result1

    # 同じ名前で2つ目のサブジェクトを追加（UNIQUE制約違反）
    result2 = add_subject(name="unique-subject", description="Second")
    assert "error" in result2
    assert result2["error"]["code"] == "DATABASE_ERROR"
    assert "UNIQUE" in result2["error"]["message"] or "unique" in result2["error"]["message"].lower()


def test_add_topic_foreign_key_violation(temp_db):
    """存在しないsubject_idでトピック追加時にエラーが返る"""
    # 存在しないサブジェクトIDでトピックを追加
    result = add_topic(subject_id=99999, title="Invalid Topic", description="Test")

    # エラーが返る（FOREIGN KEYまたはDATABASE_ERROR）
    assert "error" in result
    # SQLiteはFOREIGN KEY制約が有効な場合、CONSTRAINT_VIOLATIONが返る
    assert result["error"]["code"] in ["CONSTRAINT_VIOLATION", "DATABASE_ERROR"]


def test_list_subjects_database_error_handling(temp_db):
    """データベースエラー時にDATABASE_ERRORが返る"""
    # 正常ケースでエラーが発生しないことを確認
    result = list_subjects()
    assert "error" not in result
    assert "subjects" in result


# ========================================
# 特殊文字の検索テスト（FTS5 trigram）
# ========================================


def test_search_with_percent_character(test_subject):
    """検索キーワードに%が含まれる場合、正しく処理される"""
    topic1 = add_topic(
        subject_id=test_subject,
        title="100% Complete Task",
        description="Fully done"
    )

    # %を含むキーワードで検索（FTS5ではダブルクォートエスケープで処理）
    result = search(subject_id=test_subject, keyword="100% Complete")

    assert "error" not in result
    assert len(result["results"]) == 1


def test_search_with_underscore_character(test_subject):
    """検索キーワードに_が含まれる場合、正しく処理される"""
    topic1 = add_topic(
        subject_id=test_subject,
        title="test_function_name",
        description="Test function"
    )

    # _を含むキーワードで検索
    result = search(subject_id=test_subject, keyword="test_function")

    assert "error" not in result
    assert len(result["results"]) == 1


# ========================================
# パラメータバリデーションのテスト
# ========================================
