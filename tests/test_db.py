"""データベース機能のテスト"""
import os
import tempfile
from pathlib import Path
import pytest
from src.db import get_db_path, get_connection, init_database, execute_query, execute_insert


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


def test_get_db_path_with_env():
    """環境変数が設定されている場合、その値を返す"""
    test_path = "/tmp/test.db"
    os.environ["DISCUSSION_DB_PATH"] = test_path
    try:
        assert get_db_path() == test_path
    finally:
        del os.environ["DISCUSSION_DB_PATH"]


def test_get_db_path_default():
    """環境変数が未設定の場合、デフォルトパスを返す"""
    if "DISCUSSION_DB_PATH" in os.environ:
        del os.environ["DISCUSSION_DB_PATH"]

    path = get_db_path()
    assert path.endswith(".claude/.claude-code-memory/discussion.db")


def test_init_database(temp_db):
    """データベース初期化が成功する"""
    conn = get_connection()
    try:
        # テーブルが作成されていることを確認
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "subjects" in tables
        assert "discussion_topics" in tables
        assert "discussion_logs" in tables
        assert "decisions" in tables
    finally:
        conn.close()


def test_execute_insert_and_query(temp_db):
    """INSERT と SELECT が正しく動作する"""
    # サブジェクトを追加
    subject_id = execute_insert(
        "INSERT INTO subjects (name, description) VALUES (?, ?)",
        ("test-subject", "テストサブジェクト"),
    )
    assert subject_id > 0

    # 追加したサブジェクトを取得
    rows = execute_query("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    assert len(rows) == 1
    assert rows[0]["name"] == "test-subject"
    assert rows[0]["description"] == "テストサブジェクト"


def test_get_connection_returns_row_factory(temp_db):
    """接続が Row factory を使用している"""
    conn = get_connection()
    try:
        # サブジェクトを追加
        conn.execute(
            "INSERT INTO subjects (name, description) VALUES (?, ?)", ("test-subject", "Test description")
        )
        conn.commit()

        # Row として取得できることを確認（追加したサブジェクトを名前で検索）
        cursor = conn.execute("SELECT * FROM subjects WHERE name = 'test-subject'")
        row = cursor.fetchone()
        assert row["name"] == "test-subject"  # 辞書ライクなアクセス
    finally:
        conn.close()


def test_init_database_seeds_initial_data(temp_db):
    """init_database()で初期データ（first_subject, first_topic）が投入される"""
    conn = get_connection()
    try:
        # first_subjectが存在することを確認
        cursor = conn.execute("SELECT * FROM subjects WHERE name = 'first_subject'")
        subject = cursor.fetchone()
        assert subject is not None
        assert "サンプルのサブジェクト" in subject["description"]
        assert "取り組み・関心事" in subject["description"]

        # first_topicが存在することを確認
        cursor = conn.execute("SELECT * FROM discussion_topics WHERE title = 'first_topic'")
        topic = cursor.fetchone()
        assert topic is not None
        assert topic["subject_id"] == subject["id"]
        assert "サンプルのトピック" in topic["description"]
        assert "一言で表すと" in topic["description"]
    finally:
        conn.close()


def test_init_database_multiple_calls_no_duplicate(temp_db):
    """init_database()を複数回実行しても初期データが重複しない"""
    # temp_dbフィクスチャ内で既に1回init_database()が呼ばれている

    # 2回目の呼び出し
    init_database()

    # 3回目の呼び出し
    init_database()

    conn = get_connection()
    try:
        # first_subjectが1件のみであることを確認
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM subjects WHERE name = 'first_subject'")
        row = cursor.fetchone()
        assert row["cnt"] == 1

        # first_topicが1件のみであることを確認
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM discussion_topics WHERE title = 'first_topic'")
        row = cursor.fetchone()
        assert row["cnt"] == 1
    finally:
        conn.close()
