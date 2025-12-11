# 作業ログ: PR #3 トピック管理API（書き込み系）

**日付**: 2025-12-11
**担当**: Claude Code
**ブランチ**: feature/pr3-topic-write-api
**親ブランチ**: feature/pr2-project-api

## 実施内容

トピック管理API（書き込み系）の実装。`add-topic`, `add-log`, `add-decision`の3つのMCPツールを実装した。

### 実装したMCPツール

#### 1. add-topic
新しい議論トピックを追加するツール。

**パラメータ:**
- `project_id` (必須): プロジェクトID
- `title` (必須): トピックのタイトル
- `description` (任意): トピックの説明
- `parent_topic_id` (任意): 親トピックのID（未指定なら最上位トピック）

**返却値:**
```json
{
  "topic_id": 1,
  "project_id": 1,
  "title": "開発フローの詳細",
  "description": "...",
  "parent_topic_id": null,
  "created_at": "2025-12-10T10:00:00Z"
}
```

**機能:**
- 親子関係を持つトピックツリーの構築が可能
- プロジェクト単位でトピックを管理

#### 2. add-log
トピックに議論ログ（1やりとり）を追加するツール。

**パラメータ:**
- `topic_id` (必須): 対象トピックのID
- `content` (必須): 議論内容（マークダウン可）

**返却値:**
```json
{
  "log_id": 1,
  "topic_id": 1,
  "content": "AI: ...\nユーザー：...",
  "created_at": "2025-12-10T10:05:00Z"
}
```

**機能:**
- 議論のやりとりを時系列で記録
- 外部キー制約により存在しないトピックIDはエラー

#### 3. add-decision
決定事項を記録するツール。

**パラメータ:**
- `decision` (必須): 決定内容
- `reason` (必須): 決定の理由
- `topic_id` (任意): 関連するトピックのID

**返却値:**
```json
{
  "decision_id": 1,
  "topic_id": 1,
  "decision": "設計議論フェーズではプランモード不要。",
  "reason": "設計議論では自由に発散→収束させたい。",
  "created_at": "2025-12-10T10:10:00Z"
}
```

**機能:**
- トピックに紐づく決定事項を記録
- トピックIDなしでグローバルな決定事項も記録可能

### コード変更

#### src/main.py
- `add_topic_impl()`, `add_log_impl()`, `add_decision_impl()` 実装
- 対応するMCPツール定義を追加

#### src/db.py
- `get_connection()`に外部キー制約の有効化を追加
  - `PRAGMA foreign_keys = ON`
  - 存在しないtopic_idへの参照をエラーにする

### テストコード

#### tests/test_topic_write.py
9つのテストケース（全てPASS）:
1. `test_add_topic_success` - トピック追加の成功
2. `test_add_topic_minimal` - 必須項目のみでの追加
3. `test_add_topic_with_parent` - 親トピック指定
4. `test_add_log_success` - ログ追加の成功
5. `test_add_log_multiple` - 複数ログ追加
6. `test_add_log_invalid_topic` - 存在しないトピックIDでエラー
7. `test_add_decision_success` - 決定事項追加の成功
8. `test_add_decision_without_topic` - トピックIDなしで追加
9. `test_add_decision_multiple` - 複数決定事項の追加

### テスト結果

```
============================= test session starts ==============================
tests/test_db.py (5 tests) ............................ PASSED
tests/test_main.py (7 tests) .......................... PASSED
tests/test_topic_write.py (9 tests) ................... PASSED

============================== 21 passed in 0.35s ==============================
```

全テストPASS（DB 5 + プロジェクトAPI 7 + トピック書き込みAPI 9 = 計21テスト）

## 問題と解決

### 1. SQLiteの外部キー制約が無効
**問題**: 存在しないtopic_idを指定してもエラーにならず、レコードが挿入されてしまう

**原因**: SQLiteは外部キー制約がデフォルトで無効

**解決**: `src/db.py`の`get_connection()`で`PRAGMA foreign_keys = ON`を実行し、外部キー制約を有効化

## 次のステップ

PR #4 でトピック管理API（読み取り系：`get-topics`, `get-decided-topics`, `get-undecided-topics`, `get-topic-tree`, `get-logs`, `get-decisions`）を実装する。
