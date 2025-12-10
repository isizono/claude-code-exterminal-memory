# MCP API仕様書

## 概要

Claude Code用の外部メモリシステムのMCPツール仕様。議論トピック、議論ログ、決定事項を管理する。

### 設計原則

- **イミュータブル**: 一度記録したデータは更新・削除しない
- **議論の終了**: 削除の代わりに、決定事項（decision）に理由を記録して議論を終了させる
- **親子関係**: トピック間で親子関係を持ち、議論の文脈を保持する

---

## ツール一覧

### 書き込み系

1. [add-topic](#add-topic) - トピックを追加
2. [add-log](#add-log) - 議論ログを追加
3. [add-decision](#add-decision) - 決定事項を追加

### 読み取り系

4. [get-topics](#get-topics) - トピック一覧を取得
5. [get-logs](#get-logs) - 議論ログを取得
6. [get-decisions](#get-decisions) - 決定事項を取得

### 検索系

7. [search-topics](#search-topics) - トピックをキーワード検索
8. [search-decisions](#search-decisions) - 決定事項をキーワード検索

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
  "content": "プランモードは設計議論フェーズでは不要。実装フェーズでTODO分解時に使用する。",
  "created_at": "2025-12-10T10:05:00Z"
}
```

**Example:**

```python
result = mcp.add_log(
    topic_id=1,
    content="プランモードは設計議論フェーズでは不要。実装フェーズでTODO分解時に使用する。"
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

トピック一覧を取得する。親子関係を含めてツリー構造で返すことも可能。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `parent_topic_id` | integer | | null | 指定した親トピックの子トピックのみ取得（未指定なら全件） |
| `include_tree` | boolean | | false | trueにすると親子関係をツリー構造で返す |

**Returns (include_tree=false):**

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
      "title": "プランモードの使い方",
      "description": "...",
      "parent_topic_id": 1,
      "created_at": "2025-12-10T10:01:00Z"
    }
  ]
}
```

**Returns (include_tree=true):**

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
        }
      ]
    }
  ]
}
```

**Example:**

```python
# フラットなリストで取得
result = mcp.get_topics()

# ツリー構造で取得
result = mcp.get_topics(include_tree=True)

# 特定トピックの子トピックのみ取得
result = mcp.get_topics(parent_topic_id=1)
```

---

### get-logs

指定トピックの議論ログを取得する。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `topic_id` | integer | ✓ | | 対象トピックのID |
| `limit` | integer | | 100 | 取得件数上限 |

**Returns:**

```json
{
  "logs": [
    {
      "id": 1,
      "topic_id": 1,
      "content": "プランモードは設計議論フェーズでは不要。",
      "created_at": "2025-12-10T10:05:00Z"
    },
    {
      "id": 2,
      "topic_id": 1,
      "content": "実装フェーズでTODO分解時に使用する。",
      "created_at": "2025-12-10T10:06:00Z"
    }
  ]
}
```

**Example:**

```python
result = mcp.get_logs(topic_id=1)

# 最新10件のみ取得
result = mcp.get_logs(topic_id=1, limit=10)
```

---

### get-decisions

決定事項を取得する。

**Parameters:**

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|------|------|------|------|
| `topic_id` | integer | | null | 指定トピックに関連する決定事項のみ取得（未指定なら全件） |

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
# 全決定事項を取得
result = mcp.get_decisions()

# 特定トピックの決定事項のみ取得
result = mcp.get_decisions(topic_id=1)
```

---

### search-topics

トピックをキーワード検索する。

**Parameters:**

| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `keyword` | string | ✓ | 検索キーワード（title, descriptionから部分一致） |

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
