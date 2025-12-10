"""MCPサーバーのメインエントリーポイント"""
from fastmcp import FastMCP
from typing import Optional
from src.db import execute_insert, execute_query, row_to_dict, init_database

# MCPサーバーを作成
mcp = FastMCP("Discussion Recording System")


# 実装ロジック（テストから直接呼べるようにMCPデコレータと分離）
def add_project_impl(
    name: str,
    description: Optional[str] = None,
    asana_url: Optional[str] = None,
) -> dict:
    """
    新しいプロジェクトを追加する。

    Args:
        name: プロジェクト名（ユニーク）
        description: プロジェクトの説明
        asana_url: AsanaプロジェクトタスクのURL

    Returns:
        作成されたプロジェクト情報
    """
    try:
        project_id = execute_insert(
            "INSERT INTO projects (name, description, asana_url) VALUES (?, ?, ?)",
            (name, description, asana_url),
        )

        # 作成したプロジェクトを取得
        rows = execute_query(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        if rows:
            project = row_to_dict(rows[0])
            return {
                "project_id": project["id"],
                "name": project["name"],
                "description": project["description"],
                "asana_url": project["asana_url"],
                "created_at": project["created_at"],
            }
        else:
            raise Exception("Failed to retrieve created project")

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_projects_impl(limit: int = 30) -> dict:
    """
    プロジェクト一覧を取得する。

    Args:
        limit: 取得件数上限（最大30件）

    Returns:
        プロジェクト一覧
    """
    try:
        # limitを30件に制限
        limit = min(limit, 30)

        rows = execute_query(
            "SELECT * FROM projects ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )

        projects = []
        for row in rows:
            project = row_to_dict(row)
            projects.append({
                "id": project["id"],
                "name": project["name"],
                "description": project["description"],
                "asana_url": project["asana_url"],
                "created_at": project["created_at"],
            })

        return {"projects": projects}

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def add_topic_impl(
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


def add_log_impl(topic_id: int, content: str) -> dict:
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

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def add_decision_impl(
    decision: str,
    reason: str,
    topic_id: Optional[int] = None,
) -> dict:
    """
    決定事項を記録する。

    Args:
        decision: 決定内容
        reason: 決定の理由
        topic_id: 関連するトピックのID（未指定も可）

    Returns:
        作成された決定事項情報
    """
    try:
        decision_id = execute_insert(
            "INSERT INTO decisions (topic_id, decision, reason) VALUES (?, ?, ?)",
            (topic_id, decision, reason),
        )

        # 作成した決定事項を取得
        rows = execute_query(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        )
        if rows:
            dec = row_to_dict(rows[0])
            return {
                "decision_id": dec["id"],
                "topic_id": dec["topic_id"],
                "decision": dec["decision"],
                "reason": dec["reason"],
                "created_at": dec["created_at"],
            }
        else:
            raise Exception("Failed to retrieve created decision")

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_topics_impl(
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


def get_decided_topics_impl(
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


def get_undecided_topics_impl(
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


def get_logs_impl(
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

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_decisions_impl(
    topic_id: int,
    start_id: Optional[int] = None,
    limit: int = 30,
) -> dict:
    """
    指定トピックに関連する決定事項を取得する。

    Args:
        topic_id: 対象トピックのID
        start_id: 取得開始位置の決定事項ID（ページネーション用）
        limit: 取得件数上限（最大30件）

    Returns:
        決定事項一覧
    """
    try:
        # limitを30件に制限
        limit = min(limit, 30)

        if start_id is None:
            rows = execute_query(
                """
                SELECT * FROM decisions
                WHERE topic_id = ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (topic_id, limit),
            )
        else:
            rows = execute_query(
                """
                SELECT * FROM decisions
                WHERE topic_id = ? AND id >= ?
                ORDER BY created_at ASC, id ASC
                LIMIT ?
                """,
                (topic_id, start_id, limit),
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


def get_topic_tree_impl(
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


# MCPツール定義
@mcp.tool()
def add_project(
    name: str,
    description: Optional[str] = None,
    asana_url: Optional[str] = None,
) -> dict:
    """
    新しいプロジェクトを追加する。

    Args:
        name: プロジェクト名（ユニーク）
        description: プロジェクトの説明
        asana_url: AsanaプロジェクトタスクのURL

    Returns:
        作成されたプロジェクト情報
    """
    return add_project_impl(name, description, asana_url)


@mcp.tool()
def get_projects(limit: int = 30) -> dict:
    """
    プロジェクト一覧を取得する。

    Args:
        limit: 取得件数上限（最大30件）

    Returns:
        プロジェクト一覧
    """
    return get_projects_impl(limit)


@mcp.tool()
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
    return add_topic_impl(project_id, title, description, parent_topic_id)


@mcp.tool()
def add_log(topic_id: int, content: str) -> dict:
    """
    トピックに議論ログ（1やりとり）を追加する。

    Args:
        topic_id: 対象トピックのID
        content: 議論内容（マークダウン可）

    Returns:
        作成されたログ情報
    """
    return add_log_impl(topic_id, content)


@mcp.tool()
def add_decision(
    decision: str,
    reason: str,
    topic_id: Optional[int] = None,
) -> dict:
    """
    決定事項を記録する。

    Args:
        decision: 決定内容
        reason: 決定の理由
        topic_id: 関連するトピックのID（未指定も可）

    Returns:
        作成された決定事項情報
    """
    return add_decision_impl(decision, reason, topic_id)


@mcp.tool()
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
    return get_topics_impl(project_id, parent_topic_id, limit)


@mcp.tool()
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
    return get_decided_topics_impl(project_id, parent_topic_id, limit)


@mcp.tool()
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
    return get_undecided_topics_impl(project_id, parent_topic_id, limit)


@mcp.tool()
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
    return get_logs_impl(topic_id, start_id, limit)


@mcp.tool()
def get_decisions(
    topic_id: int,
    start_id: Optional[int] = None,
    limit: int = 30,
) -> dict:
    """
    指定トピックに関連する決定事項を取得する。

    Args:
        topic_id: 対象トピックのID
        start_id: 取得開始位置の決定事項ID（ページネーション用）
        limit: 取得件数上限（最大30件）

    Returns:
        決定事項一覧
    """
    return get_decisions_impl(topic_id, start_id, limit)


@mcp.tool()
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
    return get_topic_tree_impl(project_id, topic_id, limit)
