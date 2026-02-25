"""MCPツールのテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.services.subject_service import add_subject, list_subjects


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


def test_add_subject_success(temp_db):
    """サブジェクトの追加が成功する"""
    result = add_subject(
        name="test-subject",
        description="テストサブジェクト",
    )

    assert "error" not in result
    assert result["subject_id"] > 0
    assert result["name"] == "test-subject"
    assert result["description"] == "テストサブジェクト"
    assert "created_at" in result


def test_add_subject_duplicate_name(temp_db):
    """同じ名前のサブジェクトを追加するとエラーになる"""
    # 1つ目は成功
    result1 = add_subject(name="duplicate-test", description="Test description")
    assert "error" not in result1

    # 2つ目はエラー
    result2 = add_subject(name="duplicate-test", description="Test description")
    assert "error" in result2
    assert result2["error"]["code"] == "CONSTRAINT_VIOLATION"


def test_list_subjects_includes_initial_data(temp_db):
    """初期データ（first_subject）が含まれる"""
    result = list_subjects()

    assert "error" not in result
    # 初期データとして first_subject が投入されている
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["name"] == "first_subject"
    # id + name のみ返す
    assert set(result["subjects"][0].keys()) == {"id", "name"}


def test_list_subjects_multiple(temp_db):
    """複数のサブジェクトを取得できる"""
    # 3つサブジェクトを作成（初期データの first_subject に追加）
    add_subject(name="subject-1", description="desc-1")
    add_subject(name="subject-2", description="desc-2")
    add_subject(name="subject-3", description="desc-3")

    result = list_subjects()

    assert "error" not in result
    # 初期データ(1) + 追加(3) = 4件
    assert len(result["subjects"]) == 4

    # 作成日時の降順で返る（最新が先）
    assert result["subjects"][0]["name"] == "subject-3"
    assert result["subjects"][1]["name"] == "subject-2"
    assert result["subjects"][2]["name"] == "subject-1"
    assert result["subjects"][3]["name"] == "first_subject"


def test_list_subjects_returns_all(temp_db):
    """全件取得されることを確認"""
    # 35個サブジェクトを作成（初期データの first_subject に追加）
    for i in range(35):
        add_subject(name=f"subject-{i}", description=f"Description {i}")

    result = list_subjects()

    assert "error" not in result
    # 初期データ(1) + 追加(35) = 36件
    assert len(result["subjects"]) == 36
