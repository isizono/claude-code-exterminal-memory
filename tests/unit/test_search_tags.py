"""search_tags機能のユニットテスト"""
import os
import tempfile
import pytest
from src.db import init_database, get_connection
from src.services.topic_service import add_topic
from src.services.decision_service import add_decision
from src.services.activity_service import add_activity
from src.services.discussion_log_service import add_log
from src.services.tag_service import search_tags
import src.services.embedding_service as emb


DEFAULT_TAGS = ["domain:test"]


@pytest.fixture(autouse=True)
def disable_embedding(monkeypatch):
    """embeddingサービスを無効化"""
    monkeypatch.setattr(emb, '_server_initialized', False)
    monkeypatch.setattr(emb, '_backfill_done', True)
    monkeypatch.setattr(emb, '_ensure_server_running', lambda: False)


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


def test_search_tags_basic(temp_db):
    """基本動作: タグ名部分一致で検索できる"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])
    add_topic(title="Topic 2", description="Desc", tags=["domain:testing"])

    result = search_tags("test")
    assert "error" not in result
    assert "tags" in result
    tag_names = [t["name"] for t in result["tags"]]
    assert "test" in tag_names
    assert "testing" in tag_names


def test_search_tags_score_present(temp_db):
    """各タグにscoreフィールドが含まれる"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])

    result = search_tags("test")
    assert "error" not in result
    for tag in result["tags"]:
        assert "score" in tag
        assert isinstance(tag["score"], float)
        assert tag["score"] > 0


def test_search_tags_namespace_filter(temp_db):
    """namespaceフィルタ: 指定namespaceのみ返る"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test", "intent:design"])

    result = search_tags("test", namespace="domain")
    assert "error" not in result
    for t in result["tags"]:
        assert t["namespace"] == "domain"


def test_search_tags_namespace_filter_intent(temp_db):
    """namespaceフィルタ: intentで絞り込み"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test", "intent:design"])

    result = search_tags("design", namespace="intent")
    assert "error" not in result
    assert len(result["tags"]) >= 1
    for t in result["tags"]:
        assert t["namespace"] == "intent"


def test_search_tags_namespace_filter_bare(temp_db):
    """namespace=""フィルタ: 素タグのみ返る"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test", "baretag"])

    result = search_tags("baretag", namespace="")
    assert "error" not in result
    for t in result["tags"]:
        assert t["namespace"] == ""


def test_search_tags_include_notes_false(temp_db):
    """include_notes=False（デフォルト）でnotesが返らない"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])

    result = search_tags("test")
    assert "error" not in result
    for tag in result["tags"]:
        assert "notes" not in tag


def test_search_tags_include_notes_true(temp_db):
    """include_notes=Trueでnotesが返る"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])

    result = search_tags("test", include_notes=True)
    assert "error" not in result
    for tag in result["tags"]:
        assert "notes" in tag


def test_search_tags_limit(temp_db):
    """limitパラメータが機能する"""
    # 複数タグを作成
    for i in range(5):
        add_topic(title=f"Topic {i}", description="Desc", tags=[f"search{i}"])

    result = search_tags("search", limit=3)
    assert "error" not in result
    assert len(result["tags"]) <= 3


def test_search_tags_empty_query(temp_db):
    """空クエリはエラーを返す"""
    result = search_tags("")
    assert "error" in result
    assert result["error"]["code"] == "INVALID_QUERY"


def test_search_tags_whitespace_query(temp_db):
    """空白のみのクエリはエラーを返す"""
    result = search_tags("   ")
    assert "error" in result
    assert result["error"]["code"] == "INVALID_QUERY"


def test_search_tags_no_match(temp_db):
    """マッチしない場合は空配列を返す"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])

    result = search_tags("zzzznonexistent")
    assert "error" not in result
    assert result["tags"] == []


def test_search_tags_response_format(temp_db):
    """レスポンスの各タグのフォーマット確認"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])

    result = search_tags("test")
    assert "error" not in result
    assert len(result["tags"]) >= 1
    tag = result["tags"][0]
    assert "tag" in tag
    assert "id" in tag
    assert "namespace" in tag
    assert "name" in tag
    assert "usage_count" in tag
    assert "score" in tag
    assert "canonical" in tag
    assert isinstance(tag["id"], int)
    assert isinstance(tag["usage_count"], int)
    assert isinstance(tag["score"], float)


def test_search_tags_canonical(temp_db):
    """エイリアスタグにcanonicalフィールドが含まれる"""
    from src.services.tag_service import update_tag
    add_topic(title="Topic 1", description="Desc", tags=["domain:test", "domain:testing"])
    update_tag("domain:testing", canonical="domain:test")

    result = search_tags("testing", include_notes=True)
    assert "error" not in result
    # testing タグが返ってくる場合、canonicalが設定されているはず
    testing_tag = next((t for t in result["tags"] if t["name"] == "testing"), None)
    if testing_tag:
        assert testing_tag["canonical"] == "domain:test"


def test_search_tags_usage_count(temp_db):
    """usage_countが正しくカウントされる"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:test"])
    add_topic(title="Topic 2", description="Desc", tags=["domain:test"])
    add_activity(title="Activity 1", description="Desc", tags=["domain:test"], check_in=False)

    result = search_tags("test")
    assert "error" not in result
    test_tag = next(t for t in result["tags"] if t["name"] == "test")
    # topic_tags(2) + activity_tags(1) = 3
    assert test_tag["usage_count"] == 3


def test_search_tags_bare_tag(temp_db):
    """素タグも検索できる"""
    add_topic(title="Topic 1", description="Desc", tags=["baretag"])

    result = search_tags("baretag")
    assert "error" not in result
    bare = next((t for t in result["tags"] if t["tag"] == "baretag"), None)
    assert bare is not None
    assert bare["namespace"] == ""
    assert bare["name"] == "baretag"


def test_search_tags_partial_match(temp_db):
    """部分一致で検索できる"""
    add_topic(title="Topic 1", description="Desc", tags=["domain:cc-memory"])

    result = search_tags("memory")
    assert "error" not in result
    tag_names = [t["name"] for t in result["tags"]]
    assert "cc-memory" in tag_names
