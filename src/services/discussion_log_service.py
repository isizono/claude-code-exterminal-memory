"""議論ログ管理サービス"""
import sqlite3
from typing import Optional
from src.db import execute_insert, execute_query, row_to_dict


def add_log(topic_id: int, content: str) -> dict:
    """
    トピックに議論ログ（1やりとり）を追加する。

    Args:
        topic_id: 対象トピックのID
        content: 議論内容（マークダウン可）

    Returns:
        作成されたログ情報
    """
    try:
        log_id = execute_insert(
            "INSERT INTO discussion_logs (topic_id, content) VALUES (?, ?)",
            (topic_id, content),
        )

        # 作成したログを取得
        rows = execute_query(
            "SELECT * FROM discussion_logs WHERE id = ?", (log_id,)
        )
        if rows:
            log = row_to_dict(rows[0])
            return {
                "log_id": log["id"],
                "topic_id": log["topic_id"],
                "content": log["content"],
                "created_at": log["created_at"],
            }
        else:
            raise Exception("Failed to retrieve created log")

    except sqlite3.IntegrityError as e:
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_logs(
    topic_id: int,
    start_id: Optional[int] = None,
    limit: int = 30,
) -> dict:
    """
    指定トピックの議論ログを取得する。

    Args:
        topic_id: 対象トピックのID
        start_id: 取得開始位置のログID（ページネーション用）
        limit: 取得件数上限（最大30件）

    Returns:
        議論ログ一覧
    """
    try:
        # limitを30件に制限
        limit = min(limit, 30)

        if start_id is None:
            rows = execute_query(
                """
                SELECT * FROM discussion_logs
                WHERE topic_id = ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (topic_id, limit),
            )
        else:
            rows = execute_query(
                """
                SELECT * FROM discussion_logs
                WHERE topic_id = ? AND id >= ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (topic_id, start_id, limit),
            )

        logs = []
        for row in rows:
            log = row_to_dict(row)
            logs.append({
                "id": log["id"],
                "topic_id": log["topic_id"],
                "content": log["content"],
                "created_at": log["created_at"],
            })

        return {"logs": logs}

    except sqlite3.IntegrityError as e:
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }
