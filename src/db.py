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

    # デフォルトは ~/.claude-code-memory/discussion.db
    home = Path.home()
    db_dir = home / ".claude-code-memory"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "discussion.db")


def get_connection() -> sqlite3.Connection:
    """データベース接続を取得する"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 辞書ライクなアクセスを可能にする
    return conn


def init_database() -> None:
    """データベースを初期化する（スキーマ適用）"""
    schema_path = Path(__file__).parent.parent / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def execute_query(query: str, params: tuple = ()) -> list[sqlite3.Row]:
    """SELECT クエリを実行して結果を返す"""
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()


def execute_insert(query: str, params: tuple = ()) -> int:
    """INSERT クエリを実行して新しいIDを返す"""
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """sqlite3.Row を辞書に変換する"""
    return dict(row)
