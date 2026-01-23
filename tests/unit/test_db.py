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
    assert path.endswith(".claude-code-memory/discussion.db")


def test_init_database(temp_db):
    """データベース初期化が成功する"""
    conn = get_connection()
    try:
        # テーブルが作成されていることを確認
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "projects" in tables
        assert "discussion_topics" in tables
        assert "discussion_logs" in tables
        assert "decisions" in tables
    finally:
        conn.close()


def test_execute_insert_and_query(temp_db):
    """INSERT と SELECT が正しく動作する"""
    # プロジェクトを追加
    project_id = execute_insert(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        ("test-project", "テストプロジェクト"),
    )
    assert project_id > 0

    # 追加したプロジェクトを取得
    rows = execute_query("SELECT * FROM projects WHERE id = ?", (project_id,))
    assert len(rows) == 1
    assert rows[0]["name"] == "test-project"
    assert rows[0]["description"] == "テストプロジェクト"


def test_get_connection_returns_row_factory(temp_db):
    """接続が Row factory を使用している"""
    conn = get_connection()
    try:
        # プロジェクトを追加
        conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)", ("test-project", "Test description")
        )
        conn.commit()

        # Row として取得できることを確認（追加したプロジェクトを名前で検索）
        cursor = conn.execute("SELECT * FROM projects WHERE name = 'test-project'")
        row = cursor.fetchone()
        assert row["name"] == "test-project"  # 辞書ライクなアクセス
    finally:
        conn.close()
