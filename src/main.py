"""MCPサーバーのメインエントリーポイント"""
from fastmcp import FastMCP
from typing import Literal, Optional
from src.services import (
    project_service,
    topic_service,
    discussion_log_service,
    decision_service,
    search_service,
    task_service,
    knowledge_service,
)

# ルール文字列（rules/ディレクトリの内容を統合）
RULES = """# cc-memory 運用ルール

## トピック管理
- 1トピック = 1つの論点・問題・機能
- 迷ったらトピックを切る（粗いと後で分割が大変）

## 決定事項の記録
- ユーザーと認識合わせを行い、承認を得た時点で即座にadd_decisionで記録する
- 仕様・設計方針、技術選定、スコープ、命名規約、トレードオフの選択を記録する
- 曖昧な表現（「適切に」「必要に応じて」）を避け、具体的な条件・数値で記録する
- 決定の理由（なぜその選択をしたか）を必ず含める

### 認識合わせの姿勢
- 性急に結論を出さず、懸念点・代替案・見落としを積極的に指摘する
- 論点の網羅性を意識し、関連する未検討の論点がないか確認する
- ユーザーの発言は「提案」であり、双方が合意して初めて決定事項となる

## タスクフェーズ
- 作業は「話し合い」「設計」「実装」の3フェーズに分け、混ぜない
- タスク名にはフェーズプレフィックスをつける: [議論], [設計], [実装]
- 現フェーズを完了し、ユーザー確認を得てから次フェーズに移行する
- 話し合い中に実装を始めない、設計が固まる前にコードを書かない
"""


# MCPサーバーを作成
mcp = FastMCP("cc-memory", instructions=RULES)


# MCPツール定義
@mcp.tool()
def add_project(
    name: str,
    description: str,
    asana_url: Optional[str] = None,
) -> dict:
    """
    新しいプロジェクトを追加する。

    Projectとは「独立した関心事・取り組み」の単位。リポジトリではなく「何について話すか」で区切る。

    新規作成すべきとき:
    - 既存Projectのどれとも関係ない話題が始まった
    - 別プロダクト・サービスの話になった
    - 新しいAsanaタスクに取り組む

    既存Projectを使うとき:
    - 既存Projectの関心事の「中」の話（→ add_topicで新規Topic）

    判断に迷ったらユーザーに「どのProjectで進める？」と確認すること。
    """
    return project_service.add_project(name, description, asana_url)


@mcp.tool()
def get_projects() -> dict:
    """プロジェクト一覧を取得する。"""
    return project_service.get_projects()


@mcp.tool()
def add_topic(
    project_id: int,
    title: str,
    description: str,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """新しい議論トピックを追加する。"""
    return topic_service.add_topic(project_id, title, description, parent_topic_id)


@mcp.tool()
def add_log(topic_id: int, content: str) -> dict:
    """トピックに議論ログを追加する。"""
    return discussion_log_service.add_log(topic_id, content)


@mcp.tool()
def add_decision(
    decision: str,
    reason: str,
    topic_id: Optional[int] = None,
) -> dict:
    """決定事項を記録する。"""
    return decision_service.add_decision(decision, reason, topic_id)


@mcp.tool()
def get_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """指定した親トピックの直下の子トピックを取得する。"""
    return topic_service.get_topics(project_id, parent_topic_id)


@mcp.tool()
def get_decided_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """指定した親トピックの直下の決定済みトピックのみを取得する。"""
    return topic_service.get_decided_topics(project_id, parent_topic_id)


@mcp.tool()
def get_undecided_topics(
    project_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """指定した親トピックの直下の未決定トピックのみを取得する。"""
    return topic_service.get_undecided_topics(project_id, parent_topic_id)


@mcp.tool()
def get_logs(
    topic_id: int,
    start_id: Optional[int] = None,
    limit: int = 30,
) -> dict:
    """指定トピックの議論ログを取得する。"""
    return discussion_log_service.get_logs(topic_id, start_id, limit)


@mcp.tool()
def get_decisions(
    topic_id: int,
    start_id: Optional[int] = None,
    limit: int = 30,
) -> dict:
    """指定トピックに関連する決定事項を取得する。"""
    return decision_service.get_decisions(topic_id, start_id, limit)


@mcp.tool()
def get_topic_tree(
    project_id: int,
    topic_id: int,
    limit: int = 100,
) -> dict:
    """指定したトピックを起点に、再帰的に全ツリーを取得する。"""
    return topic_service.get_topic_tree(project_id, topic_id, limit)


@mcp.tool()
def search_topics(
    project_id: int,
    keyword: str,
    limit: int = 30,
) -> dict:
    """トピックをキーワード検索する。"""
    return search_service.search_topics(project_id, keyword, limit)


@mcp.tool()
def search_decisions(
    project_id: int,
    keyword: str,
    limit: int = 30,
) -> dict:
    """決定事項をキーワード検索する。"""
    return search_service.search_decisions(project_id, keyword, limit)


@mcp.tool()
def add_task(
    project_id: int,
    title: str,
    description: str,
) -> dict:
    """
    新しいタスクを追加する。

    典型的な使い方:
    - 実装タスクを作成: add_task(project_id, "○○機能を実装", "詳細説明...")

    ワークフロー位置: 実装タスクの整理・管理開始時

    Args:
        project_id: プロジェクトID
        title: タスクのタイトル
        description: タスクの詳細説明（必須）

    Returns:
        作成されたタスク情報
    """
    return task_service.add_task(project_id, title, description)


@mcp.tool()
def get_tasks(
    project_id: int,
    status: str = "in_progress",
    limit: int = 5,
) -> dict:
    """
    タスク一覧を取得する（statusでフィルタリング可能）。

    典型的な使い方:
    - 進行中のタスク確認: get_tasks(project_id)
    - 未着手のタスク確認: get_tasks(project_id, status="pending")
    - ブロック中のタスク確認: get_tasks(project_id, status="blocked")

    ワークフロー位置: タスク状況の確認時

    Args:
        project_id: プロジェクトID
        status: フィルタするステータス（pending/in_progress/blocked/completed、デフォルト: in_progress）
        limit: 取得件数上限（デフォルト: 5）

    Returns:
        タスク一覧（total_countで該当ステータスの全件数を確認可能）
    """
    return task_service.get_tasks(project_id, status, limit)


@mcp.tool()
def update_task_status(
    task_id: int,
    new_status: str,
) -> dict:
    """
    タスクのステータスを更新する。

    典型的な使い方:
    - タスク開始: update_task_status(task_id, "in_progress")
    - タスク完了: update_task_status(task_id, "completed")
    - ブロック状態: update_task_status(task_id, "blocked")

    ワークフロー位置: タスク進行状況の更新時

    重要: blocked状態にした場合、自動的にトピックが作成され、topic_idが設定される。
    これにより、ブロック理由や解決方法を議論トピックとして記録できる。

    Args:
        task_id: タスクID
        new_status: 新しいステータス（pending/in_progress/blocked/completed）

    Returns:
        更新されたタスク情報（blocked時はtopic_idも含む）
    """
    return task_service.update_task_status(task_id, new_status)


@mcp.tool()
def add_knowledge(
    title: str,
    content: str,
    tags: list[str],
    category: Literal["references", "facts"],
) -> dict:
    """
    ナレッジをmdファイルとして保存する。

    典型的な使い方:
    - web検索結果を保存: add_knowledge("Claude Code hooks調査", "...", ["claude-code", "hooks"], "references")
    - コードベース調査結果を保存: add_knowledge("認証フローの仕組み", "...", ["auth", "architecture"], "facts")

    ワークフロー位置: リサーチ完了後、ナレッジとして記録する時

    カテゴリの選び方:
    - references: 外部情報（web検索結果、公式ドキュメント、技術記事など）
    - facts: 事実情報（コードベースの調査結果、実験・検証の記録等）

    Args:
        title: ナレッジのタイトル（そのままファイル名になる。日本語OK）
        content: 本文（マークダウン形式）
        tags: タグ一覧（検索用）
        category: カテゴリ（"references" または "facts"）

    Returns:
        保存結果（file_path, title, category, tags）
    """
    return knowledge_service.add_knowledge(title, content, tags, category)


if __name__ == "__main__":
    from src.db import init_database
    init_database()
    mcp.run()
