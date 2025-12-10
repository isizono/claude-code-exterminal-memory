# MCP API仕様書

## 概要

Claude Code用の外部メモリシステムのMCPツール仕様。議論トピック、議論ログ、決定事項を管理する。

### 設計原則

- **イミュータブル**: 一度記録したデータは更新・削除しない
- **議論の終了**: 削除の代わりに、決定事項（decision）に理由を記録して議論を終了させる
- **親子関係**: トピック間で親子関係を持ち、議論の文脈を保持する
- **議論ログのフォーマット**: 1やりとり = 1レコード。AIとユーザーの対話を記録する。

---

## ツール一覧

### 書き込み系

1. [add-topic](#add-topic) - トピックを追加
2. [add-log](#add-log) - 議論ログを追加
3. [add-decision](#add-decision) - 決定事項を追加

### 読み取り系

4. [get-topics](#get-topics) - トピック一覧を取得（1階層）
5. [get-topic-tree](#get-topic-tree) - トピックツリーを取得（再帰的）
6. [get-logs](#get-logs) - 議論ログを取得
7. [get-decisions](#get-decisions) - 決定事項を取得

### 検索系

8. [search-topics](#search-topics) - トピックをキーワード検索
9. [search-decisions](#search-decisions) - 決定事項をキーワード検索

---

## ツール詳細

### add-topic

新しい議論トピックを追加する。

**Parameters:**

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `title` | string | ✓ | トピックのタイトル（例：「開発フローの詳細」） |
| `description` | string | | トピックの説明 |
| `parent_topic_id` | integer | | 親トピックのID（未指定なら最上位トピック） |

**Returns:**

```json
{
  "topic_id": 1,
  "title": "開発フローの詳細",
  "description": "プランモードの使い方、タスク分解の粒度を決定する",
  "parent_topic_id": null,
  "created_at": "2025-12-10T10:00:00Z"
}
```

**Example:**

```python
result = mcp.add_topic(
    title="開発フローの詳細",
    description="プランモードの使い方、タスク分解の粒度を決定する"
)
```

---

### add-log

トピックに議論ログ（1やりとり）を追加する。

**議論ログのフォーマット:**

```
AI: ○○について提案します
ユーザー：××を理由にこれを拒否し、代わりに△△を提案します
```

**Parameters:**

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `topic_id` | integer | ✓ | 対象トピックのID |
| `content` | string | ✓ | 議論内容（マークダウン可） |

**Returns:**

```json
{
  "log_id": 1,
  "topic_id": 1,
  "content": "AI: プランモードは設計議論フェーズでは不要だと考えます\nユーザー：同意します。実装フェーズでTODO分解時に使用する方針にしましょう",
  "created_at": "2025-12-10T10:05:00Z"
}
```

**Example:**

```python
result = mcp.add_log(
    topic_id=1,
    content="AI: プランモードは設計議論フェーズでは不要だと考えます\nユーザー：同意します。実装フェーズでTODO分解時に使用する方針にしましょう"
)
```

---

### add-decision

決定事項を記録する。

**Parameters:**

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `topic_id` | integer | | 関連するトピックのID（未指定も可） |
| `decision` | string | ✓ | 決定内容 |
| `reason` | string | ✓ | 決定の理由 |

**Returns:**

```json
{
  "decision_id": 1,
  "topic_id": 1,
  "decision": "設計議論フェーズではプランモード不要。実装フェーズでtaskを実行する前にプランモードで具体的TODO分解を行う。",
  "reason": "設計議論では自由に発散→収束させたい。実装時は認識合わせが必要。",
  "created_at": "2025-12-10T10:10:00Z"
}
```

**Example:**

```python
result = mcp.add_decision(
    topic_id=1,
    decision="設計議論フェーズではプランモード不要。実装フェーズでtaskを実行する前にプランモードで具体的TODO分解を行う。",
    reason="設計議論では自由に発散→収束させたい。実装時は認識合わせが必要。"
)
```

---

### get-topics

指定した親トピックの直下の子トピックを取得する（1階層のみ）。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `parent_topic_id` | integer | | null | 親トピックのID（未指定なら最上位トピックのみ取得） |
| `limit` | integer | | 10 | 取得件数上限（最大10件） |

**Returns:**

```json
{
  "topics": [
    {
      "id": 1,
      "title": "開発フローの詳細",
      "description": "...",
      "parent_topic_id": null,
      "created_at": "2025-12-10T10:00:00Z"
    },
    {
      "id": 2,
      "title": "MCPツールの設計",
      "description": "...",
      "parent_topic_id": null,
      "created_at": "2025-12-10T10:01:00Z"
    }
  ]
}
```

**Example:**

```python
# 最上位トピックを取得
result = mcp.get_topics()

# 特定トピックの子トピックを取得
result = mcp.get_topics(parent_topic_id=1)
```

---

### get-topic-tree

指定したトピックを起点に、再帰的に全ツリーを取得する。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `topic_id` | integer | | null | 起点となるトピックのID（未指定なら最上位から全ツリー） |
| `limit` | integer | | 100 | 取得件数上限（最大100件） |

**Returns:**

```json
{
  "topics": [
    {
      "id": 1,
      "title": "開発フローの詳細",
      "description": "...",
      "parent_topic_id": null,
      "created_at": "2025-12-10T10:00:00Z",
      "children": [
        {
          "id": 2,
          "title": "プランモードの使い方",
          "description": "...",
          "parent_topic_id": 1,
          "created_at": "2025-12-10T10:01:00Z",
          "children": []
        },
        {
          "id": 3,
          "title": "タスク分解の粒度",
          "description": "...",
          "parent_topic_id": 1,
          "created_at": "2025-12-10T10:02:00Z",
          "children": []
        }
      ]
    }
  ]
}
```

**Example:**

```python
# 全ツリーを取得
result = mcp.get_topic_tree()

# 特定トピックを起点にツリーを取得
result = mcp.get_topic_tree(topic_id=1)
```

**Note:**

100件に達した場合、子トピックから再度`get-topic-tree`を呼び出すことで続きを取得できる。

---

### get-logs

指定トピックの議論ログを取得する。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `topic_id` | integer | ✓ | | 対象トピックのID |
| `start_id` | integer | | null | 取得開始位置のログID（ページネーション用） |
| `limit` | integer | | 30 | 取得件数上限（最大30件） |

**Returns:**

```json
{
  "logs": [
    {
      "id": 1,
      "topic_id": 1,
      "content": "AI: プランモードは設計議論フェーズでは不要だと考えます",
      "created_at": "2025-12-10T10:05:00Z"
    },
    {
      "id": 2,
      "topic_id": 1,
      "content": "ユーザー：同意します。実装フェーズでTODO分解時に使用する方針にしましょう",
      "created_at": "2025-12-10T10:06:00Z"
    }
  ]
}
```

**Example:**

```python
# 最新30件を取得
result = mcp.get_logs(topic_id=1)

# 31件目以降を取得（ページネーション）
result = mcp.get_logs(topic_id=1, start_id=31)

# 最新10件のみ取得
result = mcp.get_logs(topic_id=1, limit=10)
```

---

### get-decisions

指定トピックに関連する決定事項を取得する。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `topic_id` | integer | ✓ | | 対象トピックのID |
| `start_id` | integer | | null | 取得開始位置の決定事項ID（ページネーション用） |
| `limit` | integer | | 30 | 取得件数上限（最大30件） |

**Returns:**

```json
{
  "decisions": [
    {
      "id": 1,
      "topic_id": 1,
      "decision": "設計議論フェーズではプランモード不要。",
      "reason": "設計議論では自由に発散→収束させたい。",
      "created_at": "2025-12-10T10:10:00Z"
    }
  ]
}
```

**Example:**

```python
# 特定トピックの決定事項を取得
result = mcp.get_decisions(topic_id=1)

# ページネーション
result = mcp.get_decisions(topic_id=1, start_id=31)
```

**Note:**

全決定事項を取得したい場合は、トピックツリーを探索するか、`search-decisions`を使用する。

---

### search-topics

トピックをキーワード検索する。

**Parameters:**

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `keyword` | string | ✓ | 検索キーワード（title, descriptionから部分一致） |
| `limit` | integer | | 30 | 取得件数上限（最大30件） |

**Returns:**

```json
{
  "topics": [
    {
      "id": 1,
      "title": "開発フローの詳細",
      "description": "プランモードの使い方、タスク分解の粒度を決定する",
      "parent_topic_id": null,
      "created_at": "2025-12-10T10:00:00Z"
    }
  ]
}
```

**Example:**

```python
result = mcp.search_topics(keyword="プランモード")
```

---

### search-decisions

決定事項をキーワード検索する。

**Parameters:**

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `keyword` | string | ✓ | 検索キーワード（decision, reasonから部分一致） |
| `limit` | integer | | 30 | 取得件数上限（最大30件） |

**Returns:**

```json
{
  "decisions": [
    {
      "id": 1,
      "topic_id": 1,
      "decision": "設計議論フェーズではプランモード不要。",
      "reason": "設計議論では自由に発散→収束させたい。",
      "created_at": "2025-12-10T10:10:00Z"
    }
  ]
}
```

**Example:**

```python
result = mcp.search_decisions(keyword="プランモード")
```

---

## エラーハンドリング

すべてのツールは以下のエラーレスポンスを返す可能性がある：

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "topic_id is required"
  }
}
```

**エラーコード一覧:**

| コード | 説明 |
|--------|------|
| `INVALID_PARAMETER` | パラメータが不正 |
| `NOT_FOUND` | 指定されたリソースが存在しない |
| `DATABASE_ERROR` | データベースエラー |

---

## データベーススキーマ

参照: [docs/project-context.md](./project-context.md) の「テーブル設計」セクション

---

## 実装メモ

- **言語**: Python
- **フレームワーク**: FastMCP
- **データベース**: SQLite
- **DB接続**: sqlite3（標準ライブラリ）
- **テスト**: pytest
- **検索**: 初期実装はLIKE検索。将来的にベクトル検索（pgvector等）への移行を検討。
