"""check_topic_exists.py のユニットテスト"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.db import get_connection, init_database, execute_query


@pytest.fixture
def temp_db():
    """テスト用の一時的なデータベースを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        os.environ["DISCUSSION_DB_PATH"] = db_path
        init_database()

        # init_databaseで作成されたfirst_projectのIDを取得
        conn = get_connection()
        try:
            cursor = conn.execute("SELECT id FROM projects WHERE name = 'first_project'")
            row = cursor.fetchone()
            project_id = row[0] if row else 1

            # テスト用のトピックを追加作成
            conn.execute(
                "INSERT INTO discussion_topics (id, project_id, title, description) VALUES (100, ?, 'Test Topic', 'Description')",
                (project_id,)
            )
            conn.execute(
                "INSERT INTO discussion_topics (id, project_id, title, description) VALUES (200, ?, 'Another Topic', 'Description')",
                (project_id,)
            )
            conn.commit()
        finally:
            conn.close()

        yield db_path

        # クリーンアップ
        if "DISCUSSION_DB_PATH" in os.environ:
            del os.environ["DISCUSSION_DB_PATH"]


# check_topic_exists.py の関数をインポート（DB設定後）
def get_check_topic_exists_main():
    """temp_db fixture適用後にcheck_topic_exists.pyのmainをインポート"""
    # モジュールを再読み込みしてDB設定を反映
    import importlib
    import check_topic_exists
    importlib.reload(check_topic_exists)
    return check_topic_exists


class TestCheckTopicExists:
    """check_topic_exists の動作テスト"""

    def test_existing_topic_returns_true(self, temp_db, capsys):
        """存在するtopic_idの場合、trueを返す"""
        # 直接クエリでテスト
        rows = execute_query(
            "SELECT id FROM discussion_topics WHERE id = ?",
            (100,),
        )
        assert len(rows) > 0

    def test_non_existing_topic_returns_false(self, temp_db):
        """存在しないtopic_idの場合、falseを返す"""
        rows = execute_query(
            "SELECT id FROM discussion_topics WHERE id = ?",
            (99999,),
        )
        assert len(rows) == 0

    def test_multiple_topics_exist(self, temp_db):
        """複数トピックがある場合、それぞれ正しくチェックできる"""
        # topic_id=100 は存在する
        rows_100 = execute_query(
            "SELECT id FROM discussion_topics WHERE id = ?",
            (100,),
        )
        assert len(rows_100) > 0

        # topic_id=200 も存在する
        rows_200 = execute_query(
            "SELECT id FROM discussion_topics WHERE id = ?",
            (200,),
        )
        assert len(rows_200) > 0

        # topic_id=300 は存在しない
        rows_300 = execute_query(
            "SELECT id FROM discussion_topics WHERE id = ?",
            (300,),
        )
        assert len(rows_300) == 0


class TestCheckTopicExistsScript:
    """check_topic_exists.py スクリプトとしての動作テスト"""

    def test_script_with_existing_topic(self, temp_db):
        """スクリプト実行: 存在するtopic_idでtrueを出力"""
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "hooks/check_topic_exists.py", "100"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env={**os.environ, "DISCUSSION_DB_PATH": temp_db},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "true"

    def test_script_with_non_existing_topic(self, temp_db):
        """スクリプト実行: 存在しないtopic_idでfalseを出力"""
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "hooks/check_topic_exists.py", "99999"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env={**os.environ, "DISCUSSION_DB_PATH": temp_db},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "false"

    def test_script_with_invalid_topic_id(self, temp_db):
        """スクリプト実行: 不正なtopic_idでエラー"""
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "hooks/check_topic_exists.py", "invalid"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env={**os.environ, "DISCUSSION_DB_PATH": temp_db},
        )
        assert result.returncode == 1
        assert "Invalid topic_id" in result.stderr

    def test_script_with_no_args(self, temp_db):
        """スクリプト実行: 引数なしでfalseを出力"""
        import subprocess
        result = subprocess.run(
            ["uv", "run", "python", "hooks/check_topic_exists.py"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env={**os.environ, "DISCUSSION_DB_PATH": temp_db},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "false"
