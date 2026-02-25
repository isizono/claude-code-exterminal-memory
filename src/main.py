"""MCPサーバーのメインエントリーポイント"""
import logging
from fastmcp import FastMCP
from typing import Literal, Optional
from src.db import execute_query
from src.services import (
    subject_service,
    topic_service,
    discussion_log_service,
    decision_service,
    search_service,
    task_service,
    knowledge_service,
)

logger = logging.getLogger(__name__)

ACTIVE_PROJECT_DAYS = 7
RECENT_TOPICS_LIMIT = 3
DESC_MAX_LEN = 30


def _get_active_subjects() -> list[dict]:
    """直近7日以内にトピック更新があったサブジェクトを取得する"""
    rows = execute_query(
        """
        SELECT DISTINCT s.id, s.name
        FROM subjects s
        JOIN discussion_topics t ON s.id = t.subject_id
        WHERE t.created_at > datetime('now', ? || ' days')
        ORDER BY s.id
        """,
        (f"-{ACTIVE_PROJECT_DAYS}",),
    )
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def _get_recent_topics(subject_id: int) -> list[dict]:
    """サブジェクトの最新トピック3件を取得する"""
    rows = execute_query(
        """
        SELECT id, title, description
        FROM discussion_topics
        WHERE subject_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (subject_id, RECENT_TOPICS_LIMIT),
    )
    results = []
    for row in rows:
        desc = row["description"] or ""
        if len(desc) > DESC_MAX_LEN:
            desc = desc[:DESC_MAX_LEN] + "..."
        results.append({"id": row["id"], "title": row["title"], "description": desc})
    return results


def _get_in_progress_tasks(subject_id: int) -> list[dict]:
    """サブジェクトのin_progressタスクを取得する"""
    rows = execute_query(
        """
        SELECT id, title
        FROM tasks
        WHERE subject_id = ? AND status = 'in_progress'
        ORDER BY updated_at DESC
        """,
        (subject_id,),
    )
    return [{"id": row["id"], "title": row["title"]} for row in rows]


def _build_active_context() -> str:
    """アクティブサブジェクトのコンテキスト文字列を組み立てる"""
    try:
        subjects = _get_active_subjects()
        if not subjects:
            return ""

        lines = ["# アクティブサブジェクト（直近7日）\n"]
        for s in subjects:
            lines.append(f"## {s['name']} (id: {s['id']})")

            topics = _get_recent_topics(s["id"])
            if topics:
                lines.append("最新トピック:")
                for t in topics:
                    lines.append(f"- [{t['id']}] {t['title']}: {t['description']}")

            tasks = _get_in_progress_tasks(s["id"])
            if tasks:
                lines.append("進行中タスク:")
                for task in tasks:
                    lines.append(f"- [{task['id']}] {task['title']}")

            lines.append("")

        return "\n".join(lines)
    except Exception:
        logger.warning("Failed to build active context", exc_info=True)
        return ""


# Instructions injected into the MCP server
RULES = """# cc-memory Usage Guide

## Topic Management

You organize discussions using topics. Each topic represents a single concern, problem, or feature.
When a conversation shifts to a new subject, create a new topic rather than overloading an existing one —
splitting topics later is much harder than starting a new one.

## Recording Decisions

When you and the user reach agreement on something, record it immediately using `add_decision`.
Decisions capture what was agreed and why — design choices, technical selections, scope boundaries,
naming conventions, and trade-off resolutions.

Be specific: avoid vague language like "as appropriate" or "as needed." Use concrete conditions and values.
Always include the reasoning behind the decision, not just the outcome.

### Collaborative Decision-Making

Your role is to act as a thoughtful sparring partner, not a passive recorder.
The user's statements are proposals, not final decisions — mutual agreement is required before recording.

- Actively raise concerns, alternatives, and potential oversights
- Ensure all relevant angles are explored before converging on a decision
- Do not rush to conclusions; allow divergent discussion before narrowing down

## Task Phases

Work proceeds through three distinct phases: **discussion**, **design**, and **implementation**.
Do not mix phases — complete the current phase and get user confirmation before moving to the next.
Task names should reflect their phase with a prefix: `[議論]`, `[設計]`, `[実装]`.

When working on a task listed under "進行中タスク", use the corresponding skill based on the prefix:
- `[議論]` → use the `discussion` skill
- `[設計]` → use the `design` skill
- `[実装]` → use the `implementation` skill

## Meta Tag

You must output a meta tag at the end of every response. This tag is used by the stop hook
to track which subject and topic the current conversation belongs to.

Format: `<!-- [meta] subject: <name> (id: <N>) | topic: <name> (id: <M>) -->`

If no existing topic fits, create a new one with `add_topic` first. Never use placeholder values like "N/A".
"""


def build_instructions() -> str:
    """ルール + アクティブコンテキストを組み立てる"""
    context = _build_active_context()
    if context:
        return f"{RULES}\n{context}"
    return RULES


# MCPサーバーを作成
mcp = FastMCP("cc-memory", instructions=build_instructions())


# MCPツール定義
@mcp.tool()
def add_subject(
    name: str,
    description: str,
) -> dict:
    """
    新しいサブジェクトを追加する。

    Subjectとは「独立した関心事・取り組み」の単位。リポジトリではなく「何について話すか」で区切る。

    新規作成すべきとき:
    - 既存Subjectのどれとも関係ない話題が始まった
    - 別プロダクト・サービスの話になった
    - 新しい取り組みに着手する

    既存Subjectを使うとき:
    - 既存Subjectの関心事の「中」の話（→ add_topicで新規Topic）

    判断に迷ったらユーザーに「どのSubjectで進める？」と確認すること。
    """
    return subject_service.add_subject(name, description)


@mcp.tool()
def list_subjects() -> dict:
    """サブジェクト一覧を取得する。id + name のみ返す軽量版。"""
    return subject_service.list_subjects()


@mcp.tool()
def add_topic(
    subject_id: int,
    title: str,
    description: str,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """新しい議論トピックを追加する。"""
    return topic_service.add_topic(subject_id, title, description, parent_topic_id)


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
    subject_id: int,
    parent_topic_id: Optional[int] = None,
) -> dict:
    """指定した親トピックの直下の子トピックを取得する。"""
    return topic_service.get_topics(subject_id, parent_topic_id)


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
def search(
    subject_id: int,
    keyword: str,
    type_filter: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    サブジェクト内をキーワードで横断検索する。

    FTS5 trigramトークナイザによる部分文字列マッチ。3文字以上のキーワードを指定する。
    結果はBM25スコア順でランキングされる。
    詳細情報が必要な場合は get_by_id(type, id) で取得する。

    Args:
        subject_id: サブジェクトID
        keyword: 検索キーワード（3文字以上）
        type_filter: 検索対象の絞り込み（'topic', 'decision', 'task'。未指定で全種類）
        limit: 取得件数上限（デフォルト10件、最大50件）

    Returns:
        検索結果一覧（type, id, title, score）
    """
    return search_service.search(subject_id, keyword, type_filter, limit)


@mcp.tool()
def get_by_id(
    type: str,
    id: int,
) -> dict:
    """
    search結果の詳細情報を取得する。

    searchツールで得られたtype + idの組み合わせを指定して、
    元データの完全な情報を取得する。

    Args:
        type: データ種別（'topic', 'decision', 'task'）
        id: データのID

    Returns:
        指定した種別に応じた詳細情報
    """
    return search_service.get_by_id(type, id)


@mcp.tool()
def add_task(
    subject_id: int,
    title: str,
    description: str,
) -> dict:
    """
    新しいタスクを追加する。

    典型的な使い方:
    - 実装タスクを作成: add_task(subject_id, "○○機能を実装", "詳細説明...")

    ワークフロー位置: 実装タスクの整理・管理開始時

    Args:
        subject_id: サブジェクトID
        title: タスクのタイトル
        description: タスクの詳細説明（必須）

    Returns:
        作成されたタスク情報
    """
    return task_service.add_task(subject_id, title, description)


@mcp.tool()
def get_tasks(
    subject_id: int,
    status: str = "in_progress",
    limit: int = 5,
) -> dict:
    """
    タスク一覧を取得する（statusでフィルタリング可能）。

    典型的な使い方:
    - 進行中のタスク確認: get_tasks(subject_id)
    - 未着手のタスク確認: get_tasks(subject_id, status="pending")
    - ブロック中のタスク確認: get_tasks(subject_id, status="blocked")

    ワークフロー位置: タスク状況の確認時

    Args:
        subject_id: サブジェクトID
        status: フィルタするステータス（pending/in_progress/blocked/completed、デフォルト: in_progress）
        limit: 取得件数上限（デフォルト: 5）

    Returns:
        タスク一覧（total_countで該当ステータスの全件数を確認可能）
    """
    return task_service.get_tasks(subject_id, status, limit)


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
