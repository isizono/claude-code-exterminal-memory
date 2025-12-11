"""トピック管理API（読み取り系）のテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.services.project_service import add_project
from src.services.topic_service import (
    add_topic,
    get_topics,
    get_decided_topics,
    get_undecided_topics,
    get_topic_tree,
)
from src.services.discussion_log_service import add_log, get_logs
from src.services.decision_service import add_decision, get_decisions


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


# ========================================
# get-topics のテスト
# ========================================


def test_get_topics_empty(test_project):
    """トピックが存在しない場合、空の配列が返る"""
    result = get_topics(project_id=test_project)

    assert "error" not in result
    assert result["topics"] == []


def test_get_topics_root_level(test_project):
    """最上位トピックを取得できる"""
    # 最上位トピックを3つ作成
    topic1 = add_topic(project_id=test_project, title="Topic 1", description="Test description")
    topic2 = add_topic(project_id=test_project, title="Topic 2", description="Test description")
    topic3 = add_topic(project_id=test_project, title="Topic 3", description="Test description")

    result = get_topics(project_id=test_project)

    assert "error" not in result
    assert len(result["topics"]) == 3
    assert result["topics"][0]["id"] == topic1["topic_id"]
    assert result["topics"][1]["id"] == topic2["topic_id"]
    assert result["topics"][2]["id"] == topic3["topic_id"]


def test_get_topics_child_level(test_project):
    """子トピックを取得できる"""
    # 親トピックを作成
    parent = add_topic(project_id=test_project, title="Parent", description="Test description")

    # 子トピックを2つ作成
    child1 = add_topic(
        project_id=test_project,
        title="Child 1",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )
    child2 = add_topic(
        project_id=test_project,
        title="Child 2",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )

    result = get_topics(project_id=test_project, parent_topic_id=parent["topic_id"])

    assert "error" not in result
    assert len(result["topics"]) == 2
    assert result["topics"][0]["id"] == child1["topic_id"]
    assert result["topics"][1]["id"] == child2["topic_id"]
    assert result["topics"][0]["parent_topic_id"] == parent["topic_id"]


# ========================================
# get-decided-topics のテスト
# ========================================


def test_get_decided_topics_empty(test_project):
    """決定済みトピックが存在しない場合、空の配列が返る"""
    result = get_decided_topics(project_id=test_project)

    assert "error" not in result
    assert result["topics"] == []


def test_get_decided_topics_filters_correctly(test_project):
    """決定済みトピックのみを返す"""
    # トピックを3つ作成
    topic1 = add_topic(project_id=test_project, title="Decided Topic 1", description="Test description")
    topic2 = add_topic(project_id=test_project, title="Undecided Topic", description="Test description")
    topic3 = add_topic(project_id=test_project, title="Decided Topic 2", description="Test description")

    # topic1とtopic3に決定事項を追加
    add_decision(
        topic_id=topic1["topic_id"],
        decision="Decision 1",
        reason="Reason 1",
    )
    add_decision(
        topic_id=topic3["topic_id"],
        decision="Decision 2",
        reason="Reason 2",
    )

    result = get_decided_topics(project_id=test_project)

    assert "error" not in result
    assert len(result["topics"]) == 2
    assert result["topics"][0]["id"] == topic1["topic_id"]
    assert result["topics"][1]["id"] == topic3["topic_id"]


def test_get_decided_topics_with_parent(test_project):
    """親トピック配下の決定済みトピックを取得できる"""
    # 親トピックを作成
    parent = add_topic(project_id=test_project, title="Parent", description="Test description")

    # 子トピックを3つ作成
    child1 = add_topic(
        project_id=test_project,
        title="Decided Child 1",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )
    child2 = add_topic(
        project_id=test_project,
        title="Undecided Child",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )
    child3 = add_topic(
        project_id=test_project,
        title="Decided Child 2",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )

    # child1とchild3に決定事項を追加
    add_decision(
        topic_id=child1["topic_id"],
        decision="Decision 1",
        reason="Reason 1",
    )
    add_decision(
        topic_id=child3["topic_id"],
        decision="Decision 2",
        reason="Reason 2",
    )

    result = get_decided_topics(
        project_id=test_project, parent_topic_id=parent["topic_id"]
    )

    assert "error" not in result
    assert len(result["topics"]) == 2
    assert result["topics"][0]["id"] == child1["topic_id"]
    assert result["topics"][1]["id"] == child3["topic_id"]


# ========================================
# get-undecided-topics のテスト
# ========================================


def test_get_undecided_topics_empty(test_project):
    """未決定トピックが存在しない場合、空の配列が返る"""
    # トピックを作成して決定事項を追加
    topic = add_topic(project_id=test_project, title="Decided Topic", description="Test description")
    add_decision(
        topic_id=topic["topic_id"],
        decision="Decision",
        reason="Reason",
    )

    result = get_undecided_topics(project_id=test_project)

    assert "error" not in result
    assert result["topics"] == []


def test_get_undecided_topics_filters_correctly(test_project):
    """未決定トピックのみを返す"""
    # トピックを3つ作成
    topic1 = add_topic(project_id=test_project, title="Decided Topic", description="Test description")
    topic2 = add_topic(project_id=test_project, title="Undecided Topic 1", description="Test description")
    topic3 = add_topic(project_id=test_project, title="Undecided Topic 2", description="Test description")

    # topic1に決定事項を追加
    add_decision(
        topic_id=topic1["topic_id"],
        decision="Decision",
        reason="Reason",
    )

    result = get_undecided_topics(project_id=test_project)

    assert "error" not in result
    assert len(result["topics"]) == 2
    assert result["topics"][0]["id"] == topic2["topic_id"]
    assert result["topics"][1]["id"] == topic3["topic_id"]


# ========================================
# get-logs のテスト
# ========================================


def test_get_logs_empty(test_project):
    """ログが存在しない場合、空の配列が返る"""
    topic = add_topic(project_id=test_project, title="Topic", description="Test description")
    result = get_logs(topic_id=topic["topic_id"])

    assert "error" not in result
    assert result["logs"] == []


def test_get_logs_multiple(test_project):
    """複数のログを取得できる"""
    topic = add_topic(project_id=test_project, title="Topic", description="Test description")

    # 3つのログを追加
    log1 = add_log(topic_id=topic["topic_id"], content="Log 1")
    log2 = add_log(topic_id=topic["topic_id"], content="Log 2")
    log3 = add_log(topic_id=topic["topic_id"], content="Log 3")

    result = get_logs(topic_id=topic["topic_id"])

    assert "error" not in result
    assert len(result["logs"]) == 3
    assert result["logs"][0]["id"] == log1["log_id"]
    assert result["logs"][0]["content"] == "Log 1"
    assert result["logs"][1]["id"] == log2["log_id"]
    assert result["logs"][2]["id"] == log3["log_id"]


def test_get_logs_with_pagination(test_project):
    """ページネーションで取得できる"""
    topic = add_topic(project_id=test_project, title="Topic", description="Test description")

    # 5つのログを追加
    logs = []
    for i in range(5):
        log = add_log(topic_id=topic["topic_id"], content=f"Log {i}")
        logs.append(log)

    # 最初の3件を取得
    result1 = get_logs(topic_id=topic["topic_id"], limit=3)
    assert len(result1["logs"]) == 3

    # 4件目から取得
    result2 = get_logs(
        topic_id=topic["topic_id"],
        start_id=logs[3]["log_id"],
        limit=3,
    )
    assert len(result2["logs"]) == 2
    assert result2["logs"][0]["id"] == logs[3]["log_id"]


# ========================================
# get-decisions のテスト
# ========================================


def test_get_decisions_empty(test_project):
    """決定事項が存在しない場合、空の配列が返る"""
    topic = add_topic(project_id=test_project, title="Topic", description="Test description")
    result = get_decisions(topic_id=topic["topic_id"])

    assert "error" not in result
    assert result["decisions"] == []


def test_get_decisions_multiple(test_project):
    """複数の決定事項を取得できる"""
    topic = add_topic(project_id=test_project, title="Topic", description="Test description")

    # 3つの決定事項を追加
    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="Decision 1",
        reason="Reason 1",
    )
    dec2 = add_decision(
        topic_id=topic["topic_id"],
        decision="Decision 2",
        reason="Reason 2",
    )
    dec3 = add_decision(
        topic_id=topic["topic_id"],
        decision="Decision 3",
        reason="Reason 3",
    )

    result = get_decisions(topic_id=topic["topic_id"])

    assert "error" not in result
    assert len(result["decisions"]) == 3
    assert result["decisions"][0]["id"] == dec1["decision_id"]
    assert result["decisions"][0]["decision"] == "Decision 1"
    assert result["decisions"][1]["id"] == dec2["decision_id"]
    assert result["decisions"][2]["id"] == dec3["decision_id"]


def test_get_decisions_with_pagination(test_project):
    """ページネーションで取得できる"""
    topic = add_topic(project_id=test_project, title="Topic", description="Test description")

    # 5つの決定事項を追加
    decisions = []
    for i in range(5):
        dec = add_decision(
            topic_id=topic["topic_id"],
            decision=f"Decision {i}",
            reason=f"Reason {i}",
        )
        decisions.append(dec)

    # 最初の3件を取得
    result1 = get_decisions(topic_id=topic["topic_id"], limit=3)
    assert len(result1["decisions"]) == 3

    # 4件目から取得
    result2 = get_decisions(
        topic_id=topic["topic_id"],
        start_id=decisions[3]["decision_id"],
        limit=3,
    )
    assert len(result2["decisions"]) == 2
    assert result2["decisions"][0]["id"] == decisions[3]["decision_id"]


# ========================================
# get-topic-tree のテスト
# ========================================


def test_get_topic_tree_single_topic(test_project):
    """単一トピックのツリーを取得できる"""
    topic = add_topic(project_id=test_project, title="Root Topic", description="Test description")

    result = get_topic_tree(project_id=test_project, topic_id=topic["topic_id"])

    assert "error" not in result
    assert result["tree"]["id"] == topic["topic_id"]
    assert result["tree"]["title"] == "Root Topic"
    assert result["tree"]["children"] == []


def test_get_topic_tree_with_children(test_project):
    """子トピックを含むツリーを取得できる"""
    # 親トピックを作成
    parent = add_topic(project_id=test_project, title="Parent", description="Test description")

    # 子トピックを2つ作成
    child1 = add_topic(
        project_id=test_project,
        title="Child 1",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )
    child2 = add_topic(
        project_id=test_project,
        title="Child 2",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )

    result = get_topic_tree(project_id=test_project, topic_id=parent["topic_id"])

    assert "error" not in result
    assert result["tree"]["id"] == parent["topic_id"]
    assert len(result["tree"]["children"]) == 2
    assert result["tree"]["children"][0]["id"] == child1["topic_id"]
    assert result["tree"]["children"][0]["title"] == "Child 1"
    assert result["tree"]["children"][1]["id"] == child2["topic_id"]


def test_get_topic_tree_nested(test_project):
    """ネストされたツリーを取得できる"""
    # 親トピックを作成
    parent = add_topic(project_id=test_project, title="Parent", description="Test description")

    # 子トピックを作成
    child = add_topic(
        project_id=test_project,
        title="Child",
        description="Test description",
        parent_topic_id=parent["topic_id"],
    )

    # 孫トピックを作成
    grandchild = add_topic(
        project_id=test_project,
        title="Grandchild",
        description="Test description",
        parent_topic_id=child["topic_id"],
    )

    result = get_topic_tree(project_id=test_project, topic_id=parent["topic_id"])

    assert "error" not in result
    assert result["tree"]["id"] == parent["topic_id"]
    assert len(result["tree"]["children"]) == 1
    assert result["tree"]["children"][0]["id"] == child["topic_id"]
    assert len(result["tree"]["children"][0]["children"]) == 1
    assert result["tree"]["children"][0]["children"][0]["id"] == grandchild["topic_id"]


def test_get_topic_tree_with_limit(test_project):
    """limitを超える場合は制限される"""
    # 親トピックを作成
    parent = add_topic(project_id=test_project, title="Parent", description="Test description")

    # 子トピックを5つ作成
    for i in range(5):
        add_topic(
            project_id=test_project,
            title=f"Child {i}",
            description="Test description",
            parent_topic_id=parent["topic_id"],
        )

    # limit=3で取得（親1 + 子2）
    result = get_topic_tree(project_id=test_project, topic_id=parent["topic_id"], limit=3)

    assert "error" not in result
    assert result["tree"]["id"] == parent["topic_id"]
    # limit=3なので、親1つ + 子2つまで
    assert len(result["tree"]["children"]) == 2


def test_get_topic_tree_not_found(test_project):
    """存在しないトピックIDでエラーになる"""
    result = get_topic_tree(project_id=test_project, topic_id=99999)

    assert "error" in result
    assert result["error"]["code"] == "NOT_FOUND"
