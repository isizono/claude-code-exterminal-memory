"""議論トピック管理サービス"""
from typing import Optional
from src.db import execute_insert, execute_query, row_to_dict


def add_topic(
    project_id: int,
    title: str,
    description: Optional[str] = None,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """
    新しい議論トピックを追加する。

    Args:
        project_id: プロジェクトID
        title: トピックのタイトル
        description: トピックの説明
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
    limit: int = 10,
) -> dict:
    """
    指定した親トピックの直下の子トピックを取得する（1階層・全件）。

    Args:
        project_id: プロジェクトID
        parent_topic_id: 親トピックのID（未指定なら最上位トピックのみ取得）
        limit: 取得件数上限（最大10件）

    Returns:
        トピック一覧
    """
    try:
        # limitを10件に制限
        limit = min(limit, 10)

        # parent_topic_id が None の場合は IS NULL を使う
        if parent_topic_id is None:
            rows = execute_query(
                """
                SELECT * FROM discussion_topics
                WHERE project_id = ? AND parent_topic_id IS NULL
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (project_id, limit),
            )
        else:
            rows = execute_query(
                """
                SELECT * FROM discussion_topics
                WHERE project_id = ? AND parent_topic_id = ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (project_id, parent_topic_id, limit),
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

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_decided_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """
    指定した親トピックの直下の子トピックのうち、決定済み（decisionが存在する）トピックのみを取得する（1階層）。

    Args:
        project_id: プロジェクトID
        parent_topic_id: 親トピックのID（未指定なら最上位トピックのみ取得）
        limit: 取得件数上限（最大10件）

    Returns:
        決定済みトピック一覧
    """
    try:
        # limitを10件に制限
        limit = min(limit, 10)

        # parent_topic_id が None の場合は IS NULL を使う
        if parent_topic_id is None:
            rows = execute_query(
                """
                SELECT dt.* FROM discussion_topics dt
                WHERE dt.project_id = ? AND dt.parent_topic_id IS NULL
                  AND EXISTS (SELECT 1 FROM decisions d WHERE d.topic_id = dt.id)
                ORDER BY dt.created_at ASC, dt.id ASC
                LIMIT ?
                """,
                (project_id, limit),
            )
        else:
            rows = execute_query(
                """
                SELECT dt.* FROM discussion_topics dt
                WHERE dt.project_id = ? AND dt.parent_topic_id = ?
                  AND EXISTS (SELECT 1 FROM decisions d WHERE d.topic_id = dt.id)
                ORDER BY dt.created_at ASC, dt.id ASC
                LIMIT ?
                """,
                (project_id, parent_topic_id, limit),
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

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_undecided_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """
    指定した親トピックの直下の子トピックのうち、未決定（decisionが存在しない）トピックのみを取得する（1階層）。

    Args:
        project_id: プロジェクトID
        parent_topic_id: 親トピックのID（未指定なら最上位トピックのみ取得）
        limit: 取得件数上限（最大10件）

    Returns:
        未決定トピック一覧
    """
    try:
        # limitを10件に制限
        limit = min(limit, 10)

        # parent_topic_id が None の場合は IS NULL を使う
        if parent_topic_id is None:
            rows = execute_query(
                """
                SELECT dt.* FROM discussion_topics dt
                WHERE dt.project_id = ? AND dt.parent_topic_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.topic_id = dt.id)
                ORDER BY dt.created_at ASC, dt.id ASC
                LIMIT ?
                """,
                (project_id, limit),
            )
        else:
            rows = execute_query(
                """
                SELECT dt.* FROM discussion_topics dt
                WHERE dt.project_id = ? AND dt.parent_topic_id = ?
                  AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.topic_id = dt.id)
                ORDER BY dt.created_at ASC, dt.id ASC
                LIMIT ?
                """,
                (project_id, parent_topic_id, limit),
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

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def _build_topic_tree_recursive(
    topic_id: int,
    project_id: int,
    collected_count: list[int],
    limit: int,
) -> Optional[dict]:
    """
    トピックツリーを再帰的に構築する（内部ヘルパー関数）。

    Args:
        topic_id: 起点となるトピックのID
        project_id: プロジェクトID
        collected_count: 収集したトピック数のカウンタ（リストで参照渡し）
        limit: 収集上限

    Returns:
        トピックツリー（limit到達時はNone）
    """
    # limit到達チェック
    if collected_count[0] >= limit:
        return None

    # 起点となるトピックを取得
    rows = execute_query(
        "SELECT * FROM discussion_topics WHERE id = ? AND project_id = ?",
        (topic_id, project_id),
    )

    if not rows:
        return None

    topic = row_to_dict(rows[0])
    collected_count[0] += 1

    # トピック情報を構築
    topic_data = {
        "id": topic["id"],
        "project_id": topic["project_id"],
        "title": topic["title"],
        "description": topic["description"],
        "parent_topic_id": topic["parent_topic_id"],
        "created_at": topic["created_at"],
        "children": [],
    }

    # limit到達していなければ子トピックも取得
    if collected_count[0] < limit:
        child_rows = execute_query(
            """
            SELECT * FROM discussion_topics
            WHERE parent_topic_id = ? AND project_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (topic_id, project_id),
        )

        for child_row in child_rows:
            if collected_count[0] >= limit:
                break

            child_topic = row_to_dict(child_row)
            child_tree = _build_topic_tree_recursive(
                child_topic["id"],
                project_id,
                collected_count,
                limit,
            )

            if child_tree is not None:
                topic_data["children"].append(child_tree)

    return topic_data


def get_topic_tree(
    project_id: int,
    topic_id: int,
    limit: int = 100,
) -> dict:
    """
    指定したトピックを起点に、再帰的に全ツリーを取得する。

    Args:
        project_id: プロジェクトID
        topic_id: 起点となるトピックのID
        limit: 取得件数上限（最大100件）

    Returns:
        トピックツリー
    """
    try:
        # limitを100件に制限
        limit = min(limit, 100)

        # 収集したトピック数をカウント（参照渡しのためリストを使用）
        collected_count = [0]

        tree = _build_topic_tree_recursive(
            topic_id,
            project_id,
            collected_count,
            limit,
        )

        if tree is None:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Topic not found or limit reached",
                }
            }

        return {"tree": tree}

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }
