"""データベース接続と初期化を管理するモジュール"""
import sqlite3
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
        # nameのUNIQUE制約を活用してIDハードコードを避ける
        conn.execute(
            """
            INSERT OR IGNORE INTO projects (name, description)
            VALUES ('first_project', 'これはサンプルのプロジェクトです。プロジェクトは1つの取り組み・関心事を表す単位で、関連するトピックを束ねるグループです。新しい取り組みや関心事が出てきたら、新しいプロジェクトを作成してください。')
            """
        )

        # first_projectのIDを取得してdiscussion_topicsに使用
        cursor = conn.execute(
            "SELECT id FROM projects WHERE name = 'first_project'"
        )
        row = cursor.fetchone()
        if row:
            project_id = row[0]
            # discussion_topicsにはtitleのUNIQUE制約がないため、存在確認してから挿入
            cursor = conn.execute(
                "SELECT id FROM discussion_topics WHERE project_id = ? AND title = 'first_topic'",
                (project_id,)
            )
            if cursor.fetchone() is None:
                conn.execute(
                    """
                    INSERT INTO discussion_topics (project_id, title, description)
                    VALUES (?, 'first_topic', 'これはサンプルのトピックです。トピックは「この会話を一言で表すと？」に答えられる粒度が目安です。例：「[議論] ユーザー認証に使う外部サービスの選定」「[設計] エラーAPIのレスポンス形式」「[実装] 商品詳細→カート画面遷移時のクラッシュ」など。新しい話題が出てきたら、新しいトピックを作成してください。話題がプロジェクトの範囲を超えたら、プロジェクトの変更も検討してください。')
                    """,
                    (project_id,)
                )
        # FTS5初期マイグレーション
        _migrate_fts5_search_index(conn)

        conn.commit()
    finally:
        conn.close()


def _check_fts5_available(conn: sqlite3.Connection) -> bool:
    """FTS5が利用可能か確認する"""
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_check USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts5_check")
        return True
    except sqlite3.OperationalError:
        return False


def _migrate_fts5_search_index(conn: sqlite3.Connection) -> None:
    """FTS5検索インデックスの初期データマイグレーション（contentless方式）"""
    if not _check_fts5_available(conn):
        logger.warning("FTS5 is not available. Skipping search index migration.")
        return

    # search_indexが空の場合のみ実行
    cursor = conn.execute("SELECT COUNT(*) FROM search_index")
    if cursor.fetchone()[0] > 0:
        return  # 既にデータがある場合はスキップ

    # topics
    conn.execute("""
        INSERT OR IGNORE INTO search_index (source_type, source_id, project_id, title)
        SELECT 'topic', id, project_id, title
        FROM discussion_topics
    """)

    # decisions（topic_id IS NOT NULLのもののみ）
    conn.execute("""
        INSERT OR IGNORE INTO search_index (source_type, source_id, project_id, title)
        SELECT 'decision', d.id, dt.project_id, d.decision
        FROM decisions d
        JOIN discussion_topics dt ON d.topic_id = dt.id
    """)

    # tasks
    conn.execute("""
        INSERT OR IGNORE INTO search_index (source_type, source_id, project_id, title)
        SELECT 'task', id, project_id, title
        FROM tasks
    """)

    # FTS5インデックスにデータを投入（contentless方式ではrebuildが使えない）
    conn.execute("""
        INSERT INTO search_index_fts (rowid, title, body)
        SELECT si.id, si.title,
          COALESCE(
            CASE si.source_type
              WHEN 'topic' THEN (SELECT description FROM discussion_topics WHERE id = si.source_id)
              WHEN 'decision' THEN (SELECT reason FROM decisions WHERE id = si.source_id)
              WHEN 'task' THEN (SELECT description FROM tasks WHERE id = si.source_id)
            END,
            ''
          )
        FROM search_index si
    """)


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
