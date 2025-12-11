"""MCPサーバーのメインエントリーポイント"""
from fastmcp import FastMCP
from typing import Optional
from src.services import (
    project_service,
    topic_service,
    discussion_log_service,
    decision_service,
    search_service,
)

# MCPサーバーを作成
mcp = FastMCP("Discussion Recording System")


# MCPツール定義
@mcp.tool()
def add_project(
    name: str,
    description: str,
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
    return project_service.add_project(name, description, asana_url)


@mcp.tool()
def get_projects() -> dict:
    """
    プロジェクト一覧を取得する（全件）。

    Returns:
        プロジェクト一覧
    """
    return project_service.get_projects()


@mcp.tool()
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
        description: トピックの説明
        parent_topic_id: 親トピックのID（未指定なら最上位トピック）

    Returns:
        作成されたトピック情報
    """
    return topic_service.add_topic(project_id, title, description, parent_topic_id)


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
    return discussion_log_service.add_log(topic_id, content)


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
    return decision_service.add_decision(decision, reason, topic_id)


@mcp.tool()
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
    return topic_service.get_topics(project_id, parent_topic_id)


@mcp.tool()
def get_decided_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """
    指定した親トピックの直下の子トピックのうち、決定済み（decisionが存在する）トピックのみを取得する（1階層）。

    Args:
        project_id: プロジェクトID
        parent_topic_id: 親トピックのID（未指定なら最上位トピックのみ取得）

    Returns:
        決定済みトピック一覧
    """
    return topic_service.get_decided_topics(project_id, parent_topic_id)


@mcp.tool()
def get_undecided_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """
    指定した親トピックの直下の子トピックのうち、未決定（decisionが存在しない）トピックのみを取得する（1階層）。

    Args:
        project_id: プロジェクトID
        parent_topic_id: 親トピックのID（未指定なら最上位トピックのみ取得）

    Returns:
        未決定トピック一覧
    """
    return topic_service.get_undecided_topics(project_id, parent_topic_id)


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
    return discussion_log_service.get_logs(topic_id, start_id, limit)


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
    return decision_service.get_decisions(topic_id, start_id, limit)


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
    return topic_service.get_topic_tree(project_id, topic_id, limit)


@mcp.tool()
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
    return search_service.search_topics(project_id, keyword, limit)


@mcp.tool()
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
    return search_service.search_decisions(project_id, keyword, limit)
