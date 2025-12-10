# 作業ログ: PR #2 プロジェクト管理API

**日付**: 2025-12-11
**担当**: Claude Code
**ブランチ**: feature/pr2-project-api
**親ブランチ**: feature/pr1-project-setup

## 実施内容

プロジェクト管理APIの実装。`add-project`と`get-projects`の2つのMCPツールを実装した。

### 実装したMCPツール

#### 1. add-project
プロジェクトを追加するツール。

**パラメータ:**
- `name` (必須): プロジェクト名（ユニーク）
- `description` (任意): プロジェクトの説明
- `asana_url` (任意): AsanaプロジェクトタスクのURL

**返却値:**
```json
{
  "project_id": 1,
  "name": "claude-code-exterminal-memory",
  "description": "MCPサーバーを作るよ〜",
  "asana_url": "https://app.asana.com/0/...",
  "created_at": "2025-12-10T10:00:00Z"
}
```

**エラー処理:**
- 重複するnameの場合は`DATABASE_ERROR`を返す
- その他のDB操作エラーも`DATABASE_ERROR`として返す

#### 2. get-projects
プロジェクト一覧を取得するツール。

**パラメータ:**
- `limit` (デフォルト: 30): 取得件数上限（最大30件）

**返却値:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "project-name",
      "description": "...",
      "asana_url": "...",
      "created_at": "..."
    }
  ]
}
```

**仕様:**
- 作成日時の降順（最新が先）で返す
- 同じ作成日時の場合はIDの降順で返す

### ソースコード

#### src/main.py
- `FastMCP`でMCPサーバーを作成
- 実装ロジック（`_impl`関数）とMCPツール（デコレータ付き関数）を分離
  - テストから直接呼べるようにするため
  - FastMCPのデコレータを使うと`FunctionTool`オブジェクトになり直接呼び出せないため

### テストコード

#### tests/test_main.py
7つのテストケース（全てPASS）:
1. `test_add_project_success` - プロジェクト追加の成功
2. `test_add_project_minimal` - 必須項目のみでの追加
3. `test_add_project_duplicate_name` - 重複name時のエラー
4. `test_get_projects_empty` - 空の場合
5. `test_get_projects_multiple` - 複数取得・順序確認
6. `test_get_projects_with_limit` - limit指定
7. `test_get_projects_limit_max_30` - limitの最大30件制限

### テスト結果

```
============================= test session starts ==============================
tests/test_main.py::test_add_project_success PASSED                      [ 14%]
tests/test_main.py::test_add_project_minimal PASSED                      [ 28%]
tests/test_main.py::test_add_project_duplicate_name PASSED               [ 42%]
tests/test_main.py::test_get_projects_empty PASSED                       [ 57%]
tests/test_main.py::test_get_projects_multiple PASSED                    [ 71%]
tests/test_main.py::test_get_projects_with_limit PASSED                  [ 85%]
tests/test_main.py::test_get_projects_limit_max_30 PASSED                [100%]

============================== 7 passed in 0.32s ===============================
```

全テストPASS（DB関連5 + API関連7 = 計12テスト）

## 問題と解決

### 1. FastMCPデコレータによる関数呼び出しエラー
**問題**: `@mcp.tool()`デコレータを使うと関数が`FunctionTool`オブジェクトになり、テストから直接呼び出せない

**解決**:
- 実装ロジックを`_impl`サフィックス付き関数に分離
- MCPツールは`_impl`関数を呼ぶラッパーとして定義
- テストでは`_impl`関数を直接インポート

### 2. 作成日時が同じ場合の順序不定
**問題**: 同一ループ内で複数レコードを作成すると`created_at`が同じになり、順序が不定

**解決**: `ORDER BY created_at DESC, id DESC`で同一日時の場合もIDの降順でソート

## 次のステップ

PR #3 でトピック管理API（書き込み系：`add-topic`, `add-log`, `add-decision`）を実装する。
