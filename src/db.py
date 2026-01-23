"""データベース接続と初期化を管理するモジュール"""
import sqlite3
import os
from pathlib import Path
from typing import Optional


def get_db_path() -> str:
    """データベースファイルのパスを取得する"""
    db_path = os.environ.get("DISCUSSION_DB_PATH")
    if db_path:
        return db_path

    # デフォルトは ~/.claude/.claude-code-memory/discussion.db
    home = Path.home()
    db_dir = home / ".claude" / ".claude-code-memory"
    db_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    return str(db_dir / "discussion.db")


def get_connection() -> sqlite3.Connection:
    """データベース接続を取得する"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 辞書ライクなアクセスを可能にする
    conn.execute("PRAGMA foreign_keys = ON")  # 外部キー制約を有効化
    return conn


def init_database() -> None:
    """データベースを初期化する（スキーマ適用と初期データ投入）"""
    schema_path = Path(__file__).parent.parent / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()

        # 初期データの投入（既存データがある場合は挿入しない）
        conn.execute(
            """
            INSERT OR IGNORE INTO projects (id, name, description)
            VALUES (1, 'first_project', 'これはサンプルのプロジェクトです。プロジェクトは関連する議論トピックをまとめる名前空間です。新しい関心事の塊が出てきたら、積極的に新しいプロジェクトを作成してください。')
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO discussion_topics (id, project_id, title, description)
            VALUES (1, 1, 'first_topic', 'これはサンプルのトピックです。トピックは「この会話、一言で何の話？」に答えられる粒度にしてください。例: 「ログイン機能の設計」「APIレスポンス形式の決定」「バグ: 画面遷移時のクラッシュ」など。新しい話題が出てきたら積極的に新しいトピックを切ってください。話題がプロジェクトの関心事からはみ出したら、プロジェクトの変更も検討してください。')
            """
        )
        conn.commit()
    finally:
        conn.close()


def execute_query(query: str, params: tuple = ()) -> list[sqlite3.Row]:
    """SELECT クエリを実行して結果を返す"""
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        return cursor.fetchall()
    except sqlite3.Error as e:
        raise sqlite3.Error(f"クエリ実行エラー: {e}") from e
    finally:
        conn.close()


def execute_insert(query: str, params: tuple = ()) -> int:
    """INSERT クエリを実行して新しいIDを返す"""
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise sqlite3.Error(f"INSERT実行エラー: {e}") from e
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """sqlite3.Row を辞書に変換する"""
    return dict(row)
