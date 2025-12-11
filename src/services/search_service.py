"""検索サービス"""
import sqlite3
from src.db import execute_query, row_to_dict


def _escape_like_pattern(s: str) -> str:
    """
    LIKE検索用のエスケープ処理。

    Args:
        s: エスケープする文字列

    Returns:
        エスケープされた文字列
    """
    return s.replace('%', r'\%').replace('_', r'\_')


def search_topics(
    project_id: int,
    keyword: str,
    limit: int = 30,
) -> dict:
    """
    トピックをキーワード検索する。

    Args:
        project_id: プロジェクトID
        keyword: 検索キーワード（title, descriptionから部分一致）
        limit: 取得件数上限（最大30件）

    Returns:
        検索結果のトピック一覧
    """
    try:
        # limitを30件に制限
        limit = min(limit, 30)

        # LIKE検索用のパターン（大文字小文字を区別しない）
        search_pattern = f"%{_escape_like_pattern(keyword)}%"

        rows = execute_query(
            """
            SELECT * FROM discussion_topics
            WHERE project_id = ?
              AND (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (project_id, search_pattern, search_pattern, limit),
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


def search_decisions(
    project_id: int,
    keyword: str,
    limit: int = 30,
) -> dict:
    """
    決定事項をキーワード検索する。

    Args:
        project_id: プロジェクトID
        keyword: 検索キーワード（decision, reasonから部分一致）
        limit: 取得件数上限（最大30件）

    Returns:
        検索結果の決定事項一覧
    """
    try:
        # limitを30件に制限
        limit = min(limit, 30)

        # LIKE検索用のパターン（大文字小文字を区別しない）
        search_pattern = f"%{_escape_like_pattern(keyword)}%"

        rows = execute_query(
            """
            SELECT d.* FROM decisions d
            JOIN discussion_topics dt ON d.topic_id = dt.id
            WHERE dt.project_id = ?
              AND (d.decision LIKE ? ESCAPE '\\' OR d.reason LIKE ? ESCAPE '\\')
            ORDER BY d.created_at DESC, d.id DESC
            LIMIT ?
            """,
            (project_id, search_pattern, search_pattern, limit),
        )

        decisions = []
        for row in rows:
            dec = row_to_dict(row)
            decisions.append({
                "id": dec["id"],
                "topic_id": dec["topic_id"],
                "decision": dec["decision"],
                "reason": dec["reason"],
                "created_at": dec["created_at"],
            })

        return {"decisions": decisions}

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
