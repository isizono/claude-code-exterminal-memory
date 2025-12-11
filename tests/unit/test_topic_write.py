"""トピック管理API（書き込み系）のテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.services.project_service import add_project
from src.services.topic_service import add_topic
from src.services.discussion_log_service import add_log
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
    result = add_project(name="test-project", description="Test project")
    return result["project_id"]


def test_add_topic_success(test_project):
    """トピックの追加が成功する"""
    result = add_topic(
        project_id=test_project,
        title="開発フローの詳細",
        description="プランモードの使い方、タスク分解の粒度を決定する",
    )

    assert "error" not in result
    assert result["topic_id"] > 0
    assert result["project_id"] == test_project
    assert result["title"] == "開発フローの詳細"
    assert result["description"] == "プランモードの使い方、タスク分解の粒度を決定する"
    assert result["parent_topic_id"] is None
    assert "created_at" in result


def test_add_topic_with_parent(test_project):
    """親トピックを指定してトピックを追加できる"""
    # 親トピックを作成
    parent = add_topic(project_id=test_project, title="親トピック", description="Test description")

    # 子トピックを作成
    result = add_topic(
        project_id=test_project,
        title="子トピック",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )

    assert "error" not in result
    assert result["parent_topic_id"] == parent["topic_id"]


def test_add_log_success(test_project):
    """議論ログの追加が成功する"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="テストトピック", description="Test description")

    # ログを追加
    result = add_log(
        topic_id=topic["topic_id"],
        content="AI: プランモードは設計議論フェーズでは不要だと考えます\nユーザー：同意します。",
    )

    assert "error" not in result
    assert result["log_id"] > 0
    assert result["topic_id"] == topic["topic_id"]
    assert "AI: プランモードは設計議論フェーズでは不要だと考えます" in result["content"]
    assert "created_at" in result


def test_add_log_multiple(test_project):
    """同じトピックに複数のログを追加できる"""
    topic = add_topic(project_id=test_project, title="テストトピック", description="Test description")

    # 3つのログを追加
    log1 = add_log(topic_id=topic["topic_id"], content="ログ1")
    log2 = add_log(topic_id=topic["topic_id"], content="ログ2")
    log3 = add_log(topic_id=topic["topic_id"], content="ログ3")

    assert "error" not in log1
    assert "error" not in log2
    assert "error" not in log3
    assert log1["log_id"] != log2["log_id"] != log3["log_id"]


def test_add_log_invalid_topic(test_project):
    """存在しないトピックIDでエラーになる"""
    result = add_log(topic_id=99999, content="test")

    assert "error" in result
    assert result["error"]["code"] == "DATABASE_ERROR"


def test_add_decision_success(test_project):
    """決定事項の追加が成功する"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="テストトピック", description="Test description")

    # 決定事項を追加
    result = add_decision(
        topic_id=topic["topic_id"],
        decision="設計議論フェーズではプランモード不要。",
        reason="設計議論では自由に発散→収束させたい。",
    )

    assert "error" not in result
    assert result["decision_id"] > 0
    assert result["topic_id"] == topic["topic_id"]
    assert result["decision"] == "設計議論フェーズではプランモード不要。"
    assert result["reason"] == "設計議論では自由に発散→収束させたい。"
    assert "created_at" in result


def test_add_decision_without_topic(temp_db):
    """トピックIDなしで決定事項を追加できる"""
    result = add_decision(
        decision="グローバルな決定事項",
        reason="プロジェクト全体に関わる",
    )

    assert "error" not in result
    assert result["decision_id"] > 0
    assert result["topic_id"] is None


def test_add_decision_multiple(test_project):
    """複数の決定事項を追加できる"""
    topic = add_topic(project_id=test_project, title="テストトピック", description="Test description")

    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="決定1",
        reason="理由1",
    )
    dec2 = add_decision(
        topic_id=topic["topic_id"],
        decision="決定2",
        reason="理由2",
    )

    assert "error" not in dec1
    assert "error" not in dec2
    assert dec1["decision_id"] != dec2["decision_id"]
