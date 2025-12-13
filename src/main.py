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
mcp = FastMCP("claude-code-exterminal-memory")


# MCPツール定義
@mcp.tool()
def add_project(
    name: str,
    description: str,
    asana_url: Optional[str] = None,
) -> dict:
    """新しいプロジェクトを追加する。"""
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


if __name__ == "__main__":
    mcp.run()
