"""MCPツールのテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.services.project_service import add_project, get_projects


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


def test_add_project_success(temp_db):
    """プロジェクトの追加が成功する"""
    result = add_project(
        name="test-project",
        description="テストプロジェクト",
        asana_url="https://app.asana.com/0/test",
    )

    assert "error" not in result
    assert result["project_id"] > 0
    assert result["name"] == "test-project"
    assert result["description"] == "テストプロジェクト"
    assert result["asana_url"] == "https://app.asana.com/0/test"
    assert "created_at" in result


def test_add_project_duplicate_name(temp_db):
    """同じ名前のプロジェクトを追加するとエラーになる"""
    # 1つ目は成功
    result1 = add_project(name="duplicate-test", description="Test description")
    assert "error" not in result1

    # 2つ目はエラー
    result2 = add_project(name="duplicate-test", description="Test description")
    assert "error" in result2
    assert result2["error"]["code"] == "DATABASE_ERROR"


def test_get_projects_empty(temp_db):
    """プロジェクトが存在しない場合、空の配列が返る"""
    result = get_projects()

    assert "error" not in result
    assert result["projects"] == []


def test_get_projects_multiple(temp_db):
    """複数のプロジェクトを取得できる"""
    # 3つプロジェクトを作成
    add_project(name="project-1", description="desc-1")
    add_project(name="project-2", description="desc-2")
    add_project(name="project-3", description="desc-3")

    result = get_projects()

    assert "error" not in result
    assert len(result["projects"]) == 3

    # 作成日時の降順で返る（最新が先）
    assert result["projects"][0]["name"] == "project-3"
    assert result["projects"][1]["name"] == "project-2"
    assert result["projects"][2]["name"] == "project-1"


def test_get_projects_returns_all(temp_db):
    """全件取得されることを確認"""
    # 35個プロジェクトを作成
    for i in range(35):
        add_project(name=f"project-{i}", description=f"Description {i}")

    result = get_projects()

    assert "error" not in result
    assert len(result["projects"]) == 35
