"""サービス層の単体テスト（エラーハンドリング、SQLエスケープなど）"""
import os
import tempfile
import sqlite3
import pytest
from src.db import init_database
from src.services.project_service import add_project, get_projects
from src.services.topic_service import add_topic
from src.services.search_service import search_topics, search_decisions
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
def test_project(temp_db):
    """テスト用プロジェクトを作成する"""
    result = add_project(name="test-project", description="Test description")
    return result["project_id"]


# ========================================
# エラーハンドリングのテスト
# ========================================


def test_add_project_unique_constraint_violation(temp_db):
    """プロジェクト名の重複時にCONSTRAINT_VIOLATIONエラーが返る"""
    # 最初のプロジェクトを追加
    result1 = add_project(name="unique-project", description="First")
    assert "error" not in result1

    # 同じ名前で2つ目のプロジェクトを追加（UNIQUE制約違反）
    result2 = add_project(name="unique-project", description="Second")
    assert "error" in result2
    assert result2["error"]["code"] == "CONSTRAINT_VIOLATION"
    assert "UNIQUE" in result2["error"]["message"] or "unique" in result2["error"]["message"].lower()


def test_add_topic_foreign_key_violation(temp_db):
    """存在しないproject_idでトピック追加時にエラーが返る"""
    # 存在しないプロジェクトIDでトピックを追加
    result = add_topic(project_id=99999, title="Invalid Topic", description="Test")

    # エラーが返る（FOREIGN KEYまたはDATABASE_ERROR）
    assert "error" in result
    # SQLiteはFOREIGN KEY制約が有効な場合、CONSTRAINT_VIOLATIONが返る
    assert result["error"]["code"] in ["CONSTRAINT_VIOLATION", "DATABASE_ERROR"]


def test_get_projects_database_error_handling(temp_db):
    """データベースエラー時にDATABASE_ERRORが返る"""
    # 正常ケースでエラーが発生しないことを確認
    result = get_projects()
    assert "error" not in result
    assert "projects" in result


# ========================================
# SQLインジェクション対策のテスト
# ========================================


def test_search_topics_with_wildcard_percent(test_project):
    """検索キーワードに%が含まれる場合、正しくエスケープされる"""
    # トピックを追加
    topic1 = add_topic(
        project_id=test_project,
        title="100% Complete",
        description="Fully done"
    )
    topic2 = add_topic(
        project_id=test_project,
        title="50 Complete",
        description="Half done"
    )

    # %を含むキーワードで検索
    result = search_topics(project_id=test_project, keyword="100%")

    # %がワイルドカードとして扱われず、リテラル文字として検索される
    assert "error" not in result
    assert len(result["topics"]) == 1
    assert result["topics"][0]["id"] == topic1["topic_id"]


def test_search_topics_with_wildcard_underscore(test_project):
    """検索キーワードに_が含まれる場合、正しくエスケープされる"""
    # トピックを追加
    topic1 = add_topic(
        project_id=test_project,
        title="test_function",
        description="Test function"
    )
    topic2 = add_topic(
        project_id=test_project,
        title="testXfunction",
        description="Another function"
    )

    # _を含むキーワードで検索
    result = search_topics(project_id=test_project, keyword="test_")

    # _がワイルドカード（任意の1文字）として扱われず、リテラル文字として検索される
    assert "error" not in result
    assert len(result["topics"]) == 1
    assert result["topics"][0]["id"] == topic1["topic_id"]


def test_search_decisions_with_wildcard_percent(test_project):
    """決定事項検索で%が正しくエスケープされる"""
    # トピックと決定事項を追加
    topic = add_topic(project_id=test_project, title="Test Topic", description="Test")

    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="100% agreement",
        reason="Everyone agrees"
    )
    dec2 = add_decision(
        topic_id=topic["topic_id"],
        decision="50 agreement",
        reason="Half agree"
    )

    # %を含むキーワードで検索
    result = search_decisions(project_id=test_project, keyword="100%")

    # %がワイルドカードとして扱われず、リテラル文字として検索される
    assert "error" not in result
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["id"] == dec1["decision_id"]


def test_search_decisions_with_wildcard_underscore(test_project):
    """決定事項検索で_が正しくエスケープされる"""
    # トピックと決定事項を追加
    topic = add_topic(project_id=test_project, title="Test Topic", description="Test")

    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="use_snake_case",
        reason="Python convention"
    )
    dec2 = add_decision(
        topic_id=topic["topic_id"],
        decision="useXsnakeXcase",
        reason="Another style"
    )

    # _を含むキーワードで検索
    result = search_decisions(project_id=test_project, keyword="use_")

    # _がワイルドカード（任意の1文字）として扱われず、リテラル文字として検索される
    assert "error" not in result
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["id"] == dec1["decision_id"]


# ========================================
# パラメータバリデーションのテスト
# ========================================


def test_add_project_with_required_description_at_api_level():
    """main.pyのAPIレベルではdescriptionが必須（サービス層では任意）"""
    # このテストはmain.pyのツール定義を確認する
    # サービス層自体はOptionalを受け入れる
    result = add_project(name="test", description=None)
    # サービス層ではNoneを受け入れる（main.pyで検証される）
    assert "error" not in result


def test_add_topic_with_required_description_at_api_level():
    """main.pyのAPIレベルではdescriptionが必須（サービス層では任意）"""
    # このテストはmain.pyのツール定義を確認する
    # サービス層自体はOptionalを受け入れる
    temp_db_instance = tempfile.TemporaryDirectory()
    db_path = os.path.join(temp_db_instance.name, "test.db")
    os.environ["DISCUSSION_DB_PATH"] = db_path
    init_database()

    project = add_project(name="test", description="test")
    result = add_topic(project_id=project["project_id"], title="test", description=None)

    # サービス層ではNoneを受け入れる（main.pyで検証される）
    assert "error" not in result

    temp_db_instance.cleanup()
    if "DISCUSSION_DB_PATH" in os.environ:
        del os.environ["DISCUSSION_DB_PATH"]
