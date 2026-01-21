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

# MCPサーバーを作成
mcp = FastMCP("claude-code-exterminal-memory")


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
    status: Optional[str] = None,
) -> dict:
    """
    タスク一覧を取得する（statusでフィルタリング可能）。

    典型的な使い方:
    - 全タスク確認: get_tasks(project_id)
    - 進行中のタスク確認: get_tasks(project_id, status="in_progress")
    - ブロック中のタスク確認: get_tasks(project_id, status="blocked")

    ワークフロー位置: タスク状況の確認時

    Args:
        project_id: プロジェクトID
        status: フィルタするステータス（pending/in_progress/blocked/completed、未指定なら全件取得）

    Returns:
        タスク一覧
    """
    return task_service.get_tasks(project_id, status)


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


# リソース機能
@mcp.resource("docs://workflow")
def workflow_docs() -> str:
    """MCPツールを使った議論管理の典型的なフロー"""
    return """# 議論管理ワークフロー

## 1. プロジェクトの特定
まず作業対象のプロジェクトを特定する。

```
get_projects() → project_id を確認
```

## 2. 設計議論の開始
新しい議論トピックを作成する。

```
add_topic(project_id, title="○○機能の設計", description="...")
→ topic_id が返される
```

## 3. 議論のやりとり記録
AIとユーザーのやりとりを記録。

```
add_log(topic_id, content="AI: 提案\\nユーザー: フィードバック")
```

記録タイミング:
- 重要な議論の節目
- 決定事項の前提となる議論

## 4. 決定事項の記録
認識合わせ → ユーザーOK → 即座に記録。

```
add_decision(
    decision="決定内容",
    reason="理由",
    topic_id=関連トピックID
)
```

**重要**: 後回しにせず即座に記録すること。

## 5. 議論状況の確認

未決定事項:
```
get_undecided_topics(project_id)
get_undecided_topics(project_id, parent_topic_id=親ID)
```

決定済み:
```
get_decided_topics(project_id)
get_decisions(topic_id)
```

トピック構造:
```
get_topics(project_id)  # 最上位
get_topic_tree(project_id, topic_id)  # ツリー全体
```

検索:
```
search_topics(project_id, keyword="...")
search_decisions(project_id, keyword="...")
```

## 6. セッション開始時

新しいセッション開始時の推奨フロー:
1. get_projects() でプロジェクト特定
2. get_topics(project_id) で最上位トピック確認
3. get_undecided_topics(project_id) で未決定事項確認
4. 必要に応じて get_topic_tree, get_logs, get_decisions

## データベース構造

```
projects (プロジェクト)
  ├── discussion_topics (議論トピック)
  │     ├── discussion_logs (議論ログ)
  │     └── decisions (決定事項)
  └── tasks (タスク) ※未実装
```

主要な関係:
- discussion_topics.parent_topic_id → discussion_topics.id (親子関係)
- discussion_topics.project_id → projects.id
- decisions.topic_id → discussion_topics.id
"""


@mcp.resource("docs://tools-reference")
def tools_reference() -> str:
    """各MCPツールの詳細な使い方とベストプラクティス"""
    return """# MCPツール詳細リファレンス

このドキュメントでは、各MCPツールの詳細な使い方、典型的なユースケース、パラメータの説明を提供します。

## プロジェクト管理

### add_project

新しいプロジェクトを追加する。

**典型的な使い方**:
- 新プロジェクト開始時: `add_project("プロジェクト名", "説明", asana_url="...")`

**ワークフロー位置**: プロジェクト管理の最初のステップ

**パラメータ**:
- `name` (str): プロジェクト名（ユニーク）
- `description` (str): プロジェクトの説明（必須）
- `asana_url` (Optional[str]): AsanaプロジェクトタスクのURL

**返り値**: 作成されたプロジェクト情報

---

### get_projects

プロジェクト一覧を取得する（全件）。

**典型的な使い方**:
- セッション開始時にプロジェクト特定: `get_projects()` → project_id を確認

**ワークフロー位置**: 全ての議論管理の起点（最初のステップ）

**パラメータ**: なし

**返り値**: プロジェクト一覧

---

## トピック管理

### add_topic

新しい議論トピックを追加する。

**典型的な使い方**:
- 新しい設計議論を始める: `add_topic(project_id, "○○機能の設計", "...")`
- 既存トピックの詳細論点: `add_topic(project_id, "詳細設計", "...", parent_topic_id=親ID)`

**ワークフロー位置**: 議論開始時（最初のステップ）

**パラメータ**:
- `project_id` (int): プロジェクトID
- `title` (str): トピックのタイトル
- `description` (str): トピックの説明（必須）
- `parent_topic_id` (Optional[int]): 親トピックのID（未指定なら最上位トピック）

**返り値**: 作成されたトピック情報

---

### get_topics

指定した親トピックの直下の子トピックを取得する（1階層・全件）。

**典型的な使い方**:
- 最上位トピック確認: `get_topics(project_id)`
- 特定トピック配下の確認: `get_topics(project_id, parent_topic_id=親ID)`

**ワークフロー位置**: セッション開始時、トピック構造の確認時

**パラメータ**:
- `project_id` (int): プロジェクトID
- `parent_topic_id` (Optional[int]): 親トピックのID（未指定なら最上位トピックのみ取得）

**返り値**: トピック一覧

---

### get_decided_topics

指定した親トピックの直下の子トピックのうち、決定済み（decisionが存在する）トピックのみを取得する（1階層）。

**典型的な使い方**:
- 最上位の決定済み事項確認: `get_decided_topics(project_id)`
- 特定トピック配下の決定済み論点確認: `get_decided_topics(project_id, parent_topic_id=親ID)`

**ワークフロー位置**: 決定済み事項の確認時

**パラメータ**:
- `project_id` (int): プロジェクトID
- `parent_topic_id` (Optional[int]): 親トピックのID（未指定なら最上位トピックのみ取得）

**返り値**: 決定済みトピック一覧

---

### get_undecided_topics

指定した親トピックの直下の子トピックのうち、未決定（decisionが存在しない）トピックのみを取得する（1階層）。

**典型的な使い方**:
- セッション開始時に未決定事項を確認: `get_undecided_topics(project_id)`
- 特定トピック配下の未解決論点を確認: `get_undecided_topics(project_id, parent_topic_id=親ID)`

**ワークフロー位置**: セッション開始時、次に議論すべきトピックの確認時

**パラメータ**:
- `project_id` (int): プロジェクトID
- `parent_topic_id` (Optional[int]): 親トピックのID（未指定なら最上位トピックのみ取得）

**返り値**: 未決定トピック一覧

---

### get_topic_tree

指定したトピックを起点に、再帰的に全ツリーを取得する。

**典型的な使い方**:
- トピック全体の構造を把握: `get_topic_tree(project_id, topic_id)`

**ワークフロー位置**: 議論全体の俯瞰時、構造確認時

**パラメータ**:
- `project_id` (int): プロジェクトID
- `topic_id` (int): 起点となるトピックのID
- `limit` (int): 取得件数上限（最大100件、デフォルト100）

**返り値**: トピックツリー

---

### search_topics

トピックをキーワード検索する。

**典型的な使い方**:
- 過去の議論を検索: `search_topics(project_id, keyword="認証")`

**ワークフロー位置**: 関連する過去の議論を探す時

**パラメータ**:
- `project_id` (int): プロジェクトID
- `keyword` (str): 検索キーワード（title, descriptionから部分一致）
- `limit` (int): 取得件数上限（最大30件、デフォルト30）

**返り値**: 検索結果のトピック一覧

---

## 議論ログ

### add_log

トピックに議論ログ（1やりとり）を追加する。

**典型的な使い方**:
- AIとユーザーのやりとりを記録: `add_log(topic_id, "AI: 提案\\nユーザー: フィードバック")`

**ワークフロー位置**: 議論中（重要な節目で記録）

**記録タイミング**:
- 重要な議論の節目（提案→フィードバック）
- 決定事項の前提となる議論

**パラメータ**:
- `topic_id` (int): 対象トピックのID
- `content` (str): 議論内容（マークダウン可）

**返り値**: 作成されたログ情報

---

### get_logs

指定トピックの議論ログを取得する。

**典型的な使い方**:
- トピックの議論履歴を確認: `get_logs(topic_id)`
- ページング: `get_logs(topic_id, start_id=最後のID)`

**ワークフロー位置**: 議論再開時、過去の議論確認時

**パラメータ**:
- `topic_id` (int): 対象トピックのID
- `start_id` (Optional[int]): 取得開始位置のログID（ページネーション用）
- `limit` (int): 取得件数上限（最大30件、デフォルト30）

**返り値**: 議論ログ一覧

---

## 決定事項

### add_decision

決定事項を記録する。

**典型的な使い方**:
- 認識合わせ後の即座の記録: `add_decision(decision="...", reason="...", topic_id=...)`

**ワークフロー位置**: 認識合わせ→ユーザーOK直後（即座に記録）

**重要**: 後回しにせず、決定が確定した時点で記録すること

**パラメータ**:
- `decision` (str): 決定内容
- `reason` (str): 決定の理由
- `topic_id` (Optional[int]): 関連するトピックのID（未指定も可）

**返り値**: 作成された決定事項情報

---

### get_decisions

指定トピックに関連する決定事項を取得する。

**典型的な使い方**:
- トピックの決定事項を確認: `get_decisions(topic_id)`
- ページング: `get_decisions(topic_id, start_id=最後のID)`

**ワークフロー位置**: 決定済み事項の確認時

**パラメータ**:
- `topic_id` (int): 対象トピックのID
- `start_id` (Optional[int]): 取得開始位置の決定事項ID（ページネーション用）
- `limit` (int): 取得件数上限（最大30件、デフォルト30）

**返り値**: 決定事項一覧

---

### search_decisions

決定事項をキーワード検索する。

**典型的な使い方**:
- 過去の決定を検索: `search_decisions(project_id, keyword="API設計")`

**ワークフロー位置**: 関連する過去の決定事項を探す時

**パラメータ**:
- `project_id` (int): プロジェクトID
- `keyword` (str): 検索キーワード（decision, reasonから部分一致）
- `limit` (int): 取得件数上限（最大30件、デフォルト30）

**返り値**: 検索結果の決定事項一覧

---

## ベストプラクティス

### ツール選択のガイドライン

1. **セッション開始時**:
   - `get_projects()` でプロジェクトを特定
   - `get_undecided_topics(project_id)` で未決定事項を確認
   - 必要に応じて `get_topic_tree()` で全体構造を把握

2. **議論中**:
   - `add_log()` で重要なやりとりを記録
   - `add_decision()` で決定事項を即座に記録

3. **情報検索時**:
   - `search_topics()` で関連する過去の議論を探す
   - `search_decisions()` で関連する決定事項を探す

4. **階層的な議論**:
   - `add_topic()` で親子関係を作る
   - `get_topics()` で特定階層を確認
   - `get_topic_tree()` で全体を俯瞰

### 効率的なワークフロー

詳細なワークフロー例については、`docs://workflow` リソースを参照してください。
"""


if __name__ == "__main__":
    mcp.run()
