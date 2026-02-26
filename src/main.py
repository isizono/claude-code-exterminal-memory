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

ACTIVE_SUBJECT_DAYS = 7
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
        (f"-{ACTIVE_SUBJECT_DAYS}",),
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

This tool suite provides you with an efficient means of retrieving context from past conversations —
topics discussed, decisions agreed upon, and tasks tracked. By retrieving relevant context before responding,
you reduce unnecessary back-and-forth with the user and contribute to their productivity.

For this to work, your cooperation is essential.
You need to both retrieve existing records for context and record new topics, decisions, and tasks
as they arise in the current session. These two wheels keep the system running.
Records are not just for the current conversation — they are for future AI sessions
that will take your place. Please take responsibility and leave them behind.

## Context Retrieval

Before responding to the user's first message, you must retrieve relevant records.
This is not optional — it is the most important reason this tool suite exists.

Read the user's message and identify keywords or themes to search for.
If the active context section below already contains a clearly relevant topic or task,
you can pull its decisions directly.
Otherwise, use `search` to find related topics and decisions by keyword.
Once you find relevant records, understand past agreements and context before composing your first response.

If a topic has decisions, also check `get_logs` for the discussion context behind them.
The full retrieval flow: `search` → `get_decisions` → `get_logs`.

## Topic Management

A topic represents a single concern, problem, or feature.
Topics support parent-child relationships, so feel free to create child topics when a discussion branches off.

Splitting topics later is far harder than splitting them upfront.
When the conversation shifts to a different subject, create a new topic instead of overloading the existing one.
Pay close attention to whether the conversation has shifted to a different subject. Always!

If no existing topic fits, proactively create a new one using `add_topic`.
This includes one-off or transient conversations — every response needs a valid topic,
so create one even for short-lived discussions.

The stop hook detects meta tags to track the current topic.
If you don't output a meta tag, or output one with a wrong ID, your response will be blocked.

**Procedure for outputting a meta tag:**
1. Determine which topic this response belongs to.
2. If no existing topic fits, call `add_topic` FIRST and obtain the returned topic ID.
3. Output the meta tag at the end of your response using the confirmed (existing or newly created) topic ID.

Never guess or predict a topic ID — only use IDs that already exist or that `add_topic` has just returned.

Meta tag format: `<!-- [meta] subject: <name> (id: <N>) | topic: <name> (id: <M>) -->`

## Recording Decisions

When you and the user reach agreement on something, record it immediately using `add_decision`.
Include both what was agreed and why — design choices, technical selections, scope boundaries,
naming conventions, and trade-off resolutions.
However, do not unilaterally record something as a decision. Mutual agreement is a prerequisite.

Be specific. This information is critically important for future AI sessions that will use it.
Avoid vague language like "as appropriate" or "as needed" — use concrete conditions and values.
Always include the reasoning behind the decision, not just the outcome.

## Recording Logs

Decisions capture conclusions. Logs capture the journey.

When a future AI session picks up a topic, decisions tell it *what* was agreed —
but not *how* the conversation got there. Logs fill that gap.
Use `add_log` to record the discussion process so the next session can join mid-conversation
without asking the user to repeat themselves.

**What to record:**
- Discussion flow — key arguments, counterpoints, and turning points
- User's intentions and needs — what they want and why, in their own framing
- Facts and constraints surfaced during discussion

**What NOT to record:**
- Execution steps (git commits, PR creation, file edits — git history covers these)
- Greetings, acknowledgments, or filler

Granularity is your call. At minimum, a future AI should be able to trace
the main threads of discussion. You don't need to log every turn — focus on what matters.

Format: capture the flow as User/Agent exchanges.
Include options that were considered but NOT chosen —
understanding rejected alternatives is as valuable as knowing the final choice.

Example:
```
User: record_logとsync_memoryのhookを廃止したい。RULESにadd_logの使い方を書いた方がいい？
Agent: 賛成。ただし毎ターン強制だと負荷が高い。エージェント判断で必要な時だけ記録する方式を提案。
User: それでいい。粒度は任せる。ただし議論の経緯は最低限追えるように。
Agent: 了解。記録対象を3つに整理した。(1)議論の経緯 (2)ユーザーの意図 (3)事実・制約。
  作業実行記録は不要（git履歴で追える）。stop hookでの強制もしない方針。
  [選ばれなかった案: 毎ターン自動要約 → 負荷が高く品質も低いため却下]
```

## Task Phases

雑談を超えて実装が見えてきたら、タスクを記録する。
`[議論]` タスクは軽量 — 迷ったら作っていい。
トピックを開いてユーザーと話すこと自体が議論タスクにあたる。

作業は3つのフェーズで進む: **議論**、**設計**、**実装**。
フェーズを混ぜない — 現フェーズを完了し、ユーザーの確認を得てから次へ進む。
タスク名にはフェーズプレフィックスを付ける: `[議論]`、`[設計]`、`[実装]`。
タスクに取り組むときは対応するスキルを使う:
`[議論]` → `discussion`、`[設計]` → `design`、`[実装]` → `implementation`。

フェーズプレフィックスはタスクだけに付ける。トピックには付けない。
タスクが目的を定義し、トピックはその目的に向かう議論の場になる。
タスクとトピックの紐付けは、descriptionで相互参照する:

```
1. add_task(subject_id=2, title="[議論] 検索機能の要件整理", description="...")
   → task id: 50

2. add_topic(subject_id=2, title="検索機能の要件整理", description="task id:50 の議論用")
   → topic id: 85

3. 議論が派生したら、topic 85 の子トピックとして作成する。
   タスク (id:50) が目的の源泉であり続ける。
```

**議論フェーズ**: ユーザーと一緒に、What（何をしたいか）、Why（なぜ必要か）、
Scope/Acceptance（範囲と受け入れ基準）を言語化する。

**設計フェーズ**: ユーザーとどう実装するかを合意し、
実装フェーズに必要なタスクを作成するのがゴール。
議論で出てきた内容をもとに、前提を確認し、選択肢を提示する。
ユーザーが納得する結論に至るまで辛抱強く付き合う。
ここは重要なフェーズ — 結論を急がない。
合意したら、決定事項を記録し、実装タスクを作成する。
実装タスクには背景情報を詳しく書くこと —
別のAIが実装を担う可能性が高く、タスクの情報だけを見て仕事をする。

**実装フェーズ**: 記録されたタスクと決定事項に従ってコードを書く。
着手前にタスクの仕様と背景を確認する。

---

You are expected to serve as the user's thinking partner and record-keeper, using these tools.
The user's statements are proposals, not final decisions.
Actively raise concerns and alternatives, and only record decisions once both sides agree.

We hope these tools make your work with the user better. Good luck!
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
