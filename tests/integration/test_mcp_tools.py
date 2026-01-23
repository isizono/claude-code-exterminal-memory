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


def test_get_projects_includes_initial_data(temp_db):
    """初期データ（first_project）が含まれる"""
    result = get_projects()

    assert "error" not in result
    # 初期データとして first_project が投入されている
    assert len(result["projects"]) == 1
    assert result["projects"][0]["name"] == "first_project"


def test_get_projects_multiple(temp_db):
    """複数のプロジェクトを取得できる"""
    # 3つプロジェクトを作成（初期データの first_project に追加）
    add_project(name="project-1", description="desc-1")
    add_project(name="project-2", description="desc-2")
    add_project(name="project-3", description="desc-3")

    result = get_projects()

    assert "error" not in result
    # 初期データ(1) + 追加(3) = 4件
    assert len(result["projects"]) == 4

    # 作成日時の降順で返る（最新が先）
    assert result["projects"][0]["name"] == "project-3"
    assert result["projects"][1]["name"] == "project-2"
    assert result["projects"][2]["name"] == "project-1"
    assert result["projects"][3]["name"] == "first_project"


def test_get_projects_returns_all(temp_db):
    """全件取得されることを確認"""
    # 35個プロジェクトを作成（初期データの first_project に追加）
    for i in range(35):
        add_project(name=f"project-{i}", description=f"Description {i}")

    result = get_projects()

    assert "error" not in result
    # 初期データ(1) + 追加(35) = 36件
    assert len(result["projects"]) == 36
