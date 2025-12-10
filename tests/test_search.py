"""検索API（search-topics, search-decisions）のテスト"""
import os
import tempfile
import pytest
from src.db import init_database
from src.main import (
    add_project_impl as add_project,
    add_topic_impl as add_topic,
    add_decision_impl as add_decision,
    search_topics_impl as search_topics,
    search_decisions_impl as search_decisions,
)


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
    result = add_project(name="test-project")
    return result["project_id"]


# ========================================
# search-topics のテスト
# ========================================


def test_search_topics_no_results(test_project):
    """検索結果がない場合、空の配列が返る"""
    # トピックを追加（キーワードにマッチしないもの）
    add_topic(project_id=test_project, title="Database Design")

    result = search_topics(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert result["topics"] == []


def test_search_topics_by_title(test_project):
    """タイトルから検索できる"""
    # トピックを3つ追加
    topic1 = add_topic(
        project_id=test_project,
        title="プランモードの使い方",
        description="設計議論での利用方法",
    )
    topic2 = add_topic(
        project_id=test_project,
        title="Database Design",
        description="テーブル設計について",
    )
    topic3 = add_topic(
        project_id=test_project,
        title="プランモードの粒度",
        description="タスク分解の粒度",
    )

    result = search_topics(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert len(result["topics"]) == 2
    # 新しい順（created_at DESC）なので topic3, topic1 の順
    assert result["topics"][0]["id"] == topic3["topic_id"]
    assert result["topics"][1]["id"] == topic1["topic_id"]


def test_search_topics_by_description(test_project):
    """説明文から検索できる"""
    # トピックを2つ追加
    topic1 = add_topic(
        project_id=test_project,
        title="開発フロー",
        description="プランモードを使った開発フロー",
    )
    topic2 = add_topic(
        project_id=test_project,
        title="Database Design",
        description="テーブル設計について",
    )

    result = search_topics(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert len(result["topics"]) == 1
    assert result["topics"][0]["id"] == topic1["topic_id"]


def test_search_topics_case_insensitive(test_project):
    """大文字小文字を区別しない検索ができる"""
    # 英語のトピックを追加
    topic1 = add_topic(
        project_id=test_project,
        title="Database Design",
        description="Schema design for PostgreSQL",
    )

    # 小文字で検索
    result = search_topics(project_id=test_project, keyword="database")

    assert "error" not in result
    assert len(result["topics"]) == 1
    assert result["topics"][0]["id"] == topic1["topic_id"]


def test_search_topics_partial_match(test_project):
    """部分一致で検索できる"""
    # トピックを追加
    topic1 = add_topic(
        project_id=test_project,
        title="開発フローの詳細設計",
        description="プランモードの使い方",
    )

    # 「フロー」という部分文字列で検索
    result = search_topics(project_id=test_project, keyword="フロー")

    assert "error" not in result
    assert len(result["topics"]) == 1
    assert result["topics"][0]["id"] == topic1["topic_id"]


def test_search_topics_with_limit(test_project):
    """limit指定で取得件数を制限できる"""
    # 5つのトピックを追加
    for i in range(5):
        add_topic(
            project_id=test_project,
            title=f"プランモード Topic {i}",
        )

    result = search_topics(project_id=test_project, keyword="プランモード", limit=3)

    assert "error" not in result
    assert len(result["topics"]) == 3


def test_search_topics_limit_max_30(test_project):
    """limitは最大30件に制限される"""
    # 40個のトピックを追加
    for i in range(40):
        add_topic(
            project_id=test_project,
            title=f"プランモード Topic {i}",
        )

    # 50件要求しても30件まで
    result = search_topics(project_id=test_project, keyword="プランモード", limit=50)

    assert "error" not in result
    assert len(result["topics"]) == 30


def test_search_topics_project_isolation(test_project):
    """プロジェクト間で検索結果が分離される"""
    # 別のプロジェクトを作成
    project2 = add_project(name="test-project-2")["project_id"]

    # test_projectにトピックを追加
    topic1 = add_topic(
        project_id=test_project,
        title="プランモードの使い方",
    )

    # project2にトピックを追加
    topic2 = add_topic(
        project_id=project2,
        title="プランモードの粒度",
    )

    # test_projectで検索
    result = search_topics(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert len(result["topics"]) == 1
    assert result["topics"][0]["id"] == topic1["topic_id"]


# ========================================
# search-decisions のテスト
# ========================================


def test_search_decisions_no_results(test_project):
    """検索結果がない場合、空の配列が返る"""
    # トピックと決定事項を追加（キーワードにマッチしないもの）
    topic = add_topic(project_id=test_project, title="Test Topic")
    add_decision(
        topic_id=topic["topic_id"],
        decision="Use PostgreSQL",
        reason="Better performance",
    )

    result = search_decisions(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert result["decisions"] == []


def test_search_decisions_by_decision(test_project):
    """決定内容から検索できる"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="Test Topic")

    # 決定事項を3つ追加
    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="設計議論フェーズではプランモード不要",
        reason="自由に発散したい",
    )
    dec2 = add_decision(
        topic_id=topic["topic_id"],
        decision="Use PostgreSQL",
        reason="Better performance",
    )
    dec3 = add_decision(
        topic_id=topic["topic_id"],
        decision="実装フェーズでプランモード使用",
        reason="認識合わせが必要",
    )

    result = search_decisions(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert len(result["decisions"]) == 2
    # 新しい順（created_at DESC）なので dec3, dec1 の順
    assert result["decisions"][0]["id"] == dec3["decision_id"]
    assert result["decisions"][1]["id"] == dec1["decision_id"]


def test_search_decisions_by_reason(test_project):
    """決定理由から検索できる"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="Test Topic")

    # 決定事項を2つ追加
    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="設計議論フェーズではプランモード不要",
        reason="自由に発散したい",
    )
    dec2 = add_decision(
        topic_id=topic["topic_id"],
        decision="Use PostgreSQL",
        reason="Better performance",
    )

    result = search_decisions(project_id=test_project, keyword="発散")

    assert "error" not in result
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["id"] == dec1["decision_id"]


def test_search_decisions_case_insensitive(test_project):
    """大文字小文字を区別しない検索ができる"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="Test Topic")

    # 英語の決定事項を追加
    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="Use PostgreSQL",
        reason="Better performance",
    )

    # 小文字で検索
    result = search_decisions(project_id=test_project, keyword="postgresql")

    assert "error" not in result
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["id"] == dec1["decision_id"]


def test_search_decisions_partial_match(test_project):
    """部分一致で検索できる"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="Test Topic")

    # 決定事項を追加
    dec1 = add_decision(
        topic_id=topic["topic_id"],
        decision="設計議論フェーズではプランモード不要",
        reason="自由に発散→収束させたい",
    )

    # 「フェーズ」という部分文字列で検索
    result = search_decisions(project_id=test_project, keyword="フェーズ")

    assert "error" not in result
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["id"] == dec1["decision_id"]


def test_search_decisions_with_limit(test_project):
    """limit指定で取得件数を制限できる"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="Test Topic")

    # 5つの決定事項を追加
    for i in range(5):
        add_decision(
            topic_id=topic["topic_id"],
            decision=f"プランモード Decision {i}",
            reason=f"Reason {i}",
        )

    result = search_decisions(project_id=test_project, keyword="プランモード", limit=3)

    assert "error" not in result
    assert len(result["decisions"]) == 3


def test_search_decisions_limit_max_30(test_project):
    """limitは最大30件に制限される"""
    # トピックを作成
    topic = add_topic(project_id=test_project, title="Test Topic")

    # 40個の決定事項を追加
    for i in range(40):
        add_decision(
            topic_id=topic["topic_id"],
            decision=f"プランモード Decision {i}",
            reason=f"Reason {i}",
        )

    # 50件要求しても30件まで
    result = search_decisions(project_id=test_project, keyword="プランモード", limit=50)

    assert "error" not in result
    assert len(result["decisions"]) == 30


def test_search_decisions_project_isolation(test_project):
    """プロジェクト間で検索結果が分離される"""
    # 別のプロジェクトを作成
    project2 = add_project(name="test-project-2")["project_id"]

    # test_projectにトピックと決定事項を追加
    topic1 = add_topic(project_id=test_project, title="Topic 1")
    dec1 = add_decision(
        topic_id=topic1["topic_id"],
        decision="プランモード不要",
        reason="Reason 1",
    )

    # project2にトピックと決定事項を追加
    topic2 = add_topic(project_id=project2, title="Topic 2")
    dec2 = add_decision(
        topic_id=topic2["topic_id"],
        decision="プランモード使用",
        reason="Reason 2",
    )

    # test_projectで検索
    result = search_decisions(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["id"] == dec1["decision_id"]


def test_search_decisions_across_multiple_topics(test_project):
    """複数トピックにまたがって検索できる"""
    # 2つのトピックを作成
    topic1 = add_topic(project_id=test_project, title="Topic 1")
    topic2 = add_topic(project_id=test_project, title="Topic 2")

    # それぞれに決定事項を追加
    dec1 = add_decision(
        topic_id=topic1["topic_id"],
        decision="プランモード不要",
        reason="Reason 1",
    )
    dec2 = add_decision(
        topic_id=topic2["topic_id"],
        decision="プランモード使用",
        reason="Reason 2",
    )

    result = search_decisions(project_id=test_project, keyword="プランモード")

    assert "error" not in result
    assert len(result["decisions"]) == 2
    # 両方のトピックの決定事項が取得できる
    decision_ids = {d["id"] for d in result["decisions"]}
    assert dec1["decision_id"] in decision_ids
    assert dec2["decision_id"] in decision_ids
