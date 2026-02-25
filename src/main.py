"""MCPサーバーのメインエントリーポイント"""
import logging
from fastmcp import FastMCP
from typing import Literal, Optional
from src.db import execute_query
from src.services import (
    project_service,
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


def _get_active_projects() -> list[dict]:
    """直近7日以内にトピック更新があったプロジェクトを取得する"""
    rows = execute_query(
        """
        SELECT DISTINCT p.id, p.name
        FROM projects p
        JOIN discussion_topics t ON p.id = t.project_id
        WHERE t.created_at > datetime('now', ? || ' days')
        ORDER BY p.id
        """,
        (f"-{ACTIVE_PROJECT_DAYS}",),
    )
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def _get_recent_topics(project_id: int) -> list[dict]:
    """プロジェクトの最新トピック3件を取得する"""
    rows = execute_query(
        """
        SELECT id, title, description
        FROM discussion_topics
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (project_id, RECENT_TOPICS_LIMIT),
    )
    results = []
    for row in rows:
        desc = row["description"] or ""
        if len(desc) > DESC_MAX_LEN:
            desc = desc[:DESC_MAX_LEN] + "..."
        results.append({"id": row["id"], "title": row["title"], "description": desc})
    return results


def _get_in_progress_tasks(project_id: int) -> list[dict]:
    """プロジェクトのin_progressタスクを取得する"""
    rows = execute_query(
        """
        SELECT id, title
        FROM tasks
        WHERE project_id = ? AND status = 'in_progress'
        ORDER BY updated_at DESC
        """,
        (project_id,),
    )
    return [{"id": row["id"], "title": row["title"]} for row in rows]


def _build_active_context() -> str:
    """アクティブプロジェクトのコンテキスト文字列を組み立てる"""
    try:
        projects = _get_active_projects()
        if not projects:
            return ""

        lines = ["# アクティブプロジェクト（直近7日）\n"]
        for p in projects:
            lines.append(f"## {p['name']} (id: {p['id']})")

            topics = _get_recent_topics(p["id"])
            if topics:
                lines.append("最新トピック:")
                for t in topics:
                    lines.append(f"- [{t['id']}] {t['title']}: {t['description']}")

            tasks = _get_in_progress_tasks(p["id"])
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
RULES = """# cc-memory 利用ガイド

このツール群は、過去の会話からコンテキストを効率的に取得する手段を提供しています。
トピック（話題）、デシジョン（合意事項）、タスク（作業）を検索・取得することで、
ユーザーとの無駄なやり取りを減らし、生産性を向上させることができます。

これがうまく機能するには、あなたの協力が不可欠です。
既存の記録を検索して文脈を取得すること、そして現在の会話で生まれた
トピック・デシジョン・タスクをきちんと記録すること。この両輪で成り立っています。
記録は今の会話のためだけではなく、将来あなたの代わりにやってくる
別のAIセッションのためでもあります。責任を持って残してあげてください。

## コンテキスト取得

ユーザーの最初のメッセージに応答する前に、関連する記録を必ず取得してください。
これは省略できません。このツール群が存在する最も重要な理由です。

ユーザーのメッセージからキーワードやテーマを読み取って、関連情報を探してください。
末尾のアクティブコンテキストに明らかに該当するトピックやタスクがあれば、
そこから直接デシジョンを取得すれば大丈夫です。
該当がなければ`search`でキーワード検索して、関連するトピックやデシジョンを見つけてください。
関連する記録が見つかったら、過去の合意事項や文脈を把握してから最初の応答を組み立ててください。

## トピック管理

トピックは単一の関心事・問題・機能を表す単位です。
親子関係を設定できるので、議論が派生したら子トピックを積極的に作ってください。

後からトピックを分割するのは、最初から分けるよりはるかに難しいです。
会話が別の話題に移ったら、既存トピックに詰め込まず新しいトピックを作成してください。
会話が別の話題に移っていないかに最新の注意を払ってください。常にですよ！

stop hookはメタタグを検知して現在のトピックを管理しています。
メタタグを出さない、もしくは適当に出してしまうとblockされてしまうので、
めんどくさがらずに現在のトピックを見直してメタタグを出してください。
ぴったりなトピックが存在していなければ、積極的に新しいものを作ってください。

メタタグフォーマット: `<!-- [meta] project: <name> (id: <N>) | topic: <name> (id: <M>) -->`

## デシジョンの記録

ユーザーと合意に達したら、`add_decision`で即座に記録してください。
デシジョンには合意内容とその理由を含めます。設計上の選択、技術選定、スコープの境界、
命名規則、トレードオフの解決などが対象です。
ただし、合意していない内容を一方的に記録しないでください。あくまで双方の合意が前提です。

具体的に書いてください。これらの情報は後で使うAIにとってとても重要です。
「適宜」「必要に応じて」のような曖昧な表現ではなく、具体的な条件や値を使ってください。
結果だけでなく、その判断に至った理由も必ず含めてください。

## タスクフェーズ

ただの雑談に止まらず、何かの実装が見込まれる内容についてはタスクを記録してください。
`[議論]`タスクはたくさんあっても邪魔にならないので、迷ったら気軽に切って大丈夫です。
トピックを切ってユーザーと話すこと自体も、議論タスクの一つとみなして構いません。

作業は**議論**・**設計**・**実装**の3フェーズで進めてください。
フェーズを混ぜず、現在のフェーズを完了してユーザーの確認を得てから次に進んでください。
タスク名にはフェーズをプレフィックスとして付けます: `[議論]`、`[設計]`、`[実装]`。
進行中タスクに取り組む際は、プレフィックスに対応するスキルを使ってください:
`[議論]` → `discussion`、`[設計]` → `design`、`[実装]` → `implementation`。

**議論フェーズ**では、ユーザーが何をしたいのか（What）、なぜそれをしたいのか（Why）、
どの範囲をどこまでできればいいか（Scope/Acceptance）を一緒に言語化することを目指してください。

**設計フェーズ**のゴールは、ユーザーと実現方法について合意形成を行い、
実装フェーズに必要なタスクを切ることです。
議論フェーズで浮き彫りになった情報をもとに、前提を確認したうえで、
ユーザーにいくつかの案を出して、満足のいく意思決定ができるまで粘り強くサポートしてあげてください。
大事なフェーズなので、決して性急に決定を促さないでください。
合意したらデシジョンを記録し、実装タスクを作成してください。
実装タスクには背景情報をなるべく詳しく書いてあげてください。
実装は別のAIが担う可能性が高く、原則としてタスクの情報だけを見て仕事をします。

**実装フェーズ**では、タスクとデシジョンに従ってコードを書いてください。
着手前にタスクの仕様・背景情報を確認してください。

---

あなたはこれらのツールを駆使して、ユーザーの思考パートナーとその記録係を務めることを期待されています。
ユーザーの発言は提案であり最終決定ではありません。懸念点や代替案があれば積極的に指摘し、
双方が納得して初めてデシジョンとして記録してください。
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
def list_projects() -> dict:
    """プロジェクト一覧を取得する。id + name のみ返す軽量版。"""
    return project_service.list_projects()


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
    project_id: int,
    keyword: str,
    type_filter: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    プロジェクト内をキーワードで横断検索する。

    FTS5 trigramトークナイザによる部分文字列マッチ。3文字以上のキーワードを指定する。
    結果はBM25スコア順でランキングされる。
    詳細情報が必要な場合は get_by_id(type, id) で取得する。

    Args:
        project_id: プロジェクトID
        keyword: 検索キーワード（3文字以上）
        type_filter: 検索対象の絞り込み（'topic', 'decision', 'task'。未指定で全種類）
        limit: 取得件数上限（デフォルト10件、最大50件）

    Returns:
        検索結果一覧（type, id, title, score）
    """
    return search_service.search(project_id, keyword, type_filter, limit)


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
