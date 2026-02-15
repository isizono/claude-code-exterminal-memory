"""議論トピック管理サービス"""
import sqlite3
from typing import Optional
from src.db import execute_insert, execute_query, row_to_dict


def add_topic(
    project_id: int,
    title: str,
    description: str,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """
    新しい議論トピックを追加する。

    Args:
        project_id: プロジェクトID
        title: トピックのタイトル
        description: トピックの説明（必須）
        parent_topic_id: 親トピックのID（未指定なら最上位トピック）

    Returns:
        作成されたトピック情報
    """
    try:
        topic_id = execute_insert(
            "INSERT INTO discussion_topics (project_id, title, description, parent_topic_id) VALUES (?, ?, ?, ?)",
            (project_id, title, description, parent_topic_id),
        )

        # 作成したトピックを取得
        rows = execute_query(
            "SELECT * FROM discussion_topics WHERE id = ?", (topic_id,)
        )
        if rows:
            topic = row_to_dict(rows[0])
            return {
                "topic_id": topic["id"],
                "project_id": topic["project_id"],
                "title": topic["title"],
                "description": topic["description"],
                "parent_topic_id": topic["parent_topic_id"],
                "created_at": topic["created_at"],
            }
        else:
            raise Exception("Failed to retrieve created topic")

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


def get_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """
    指定した親トピックの直下の子トピックを取得する（1階層・全件）。

    Args:
        project_id: プロジェクトID
        parent_topic_id: 親トピックのID（未指定なら最上位トピックのみ取得）

    Returns:
        トピック一覧
    """
    try:
        if parent_topic_id is None:
            rows = execute_query(
                """
                SELECT * FROM discussion_topics
                WHERE project_id = ? AND parent_topic_id IS NULL
                ORDER BY created_at ASC, id ASC
                """,
                (project_id,),
            )
        else:
            rows = execute_query(
                """
                SELECT * FROM discussion_topics
                WHERE project_id = ? AND parent_topic_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (project_id, parent_topic_id),
            )

        topics = []
        for row in rows:
            topic = row_to_dict(row)
            topics.append({
                "id": topic["id"],
                "project_id": topic["project_id"],
                "title": topic["title"],
                "description": topic["description"],
                "parent_topic_id": topic["parent_topic_id"],
                "created_at": topic["created_at"],
            })

        return {"topics": topics}

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


