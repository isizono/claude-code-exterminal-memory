# 作業ログ: PR #1 プロジェクト構造とDBセットアップ

**日付**: 2025-12-11
**担当**: Claude Code
**ブランチ**: feature/pr1-project-setup

## 実施内容

議論記録システムの基盤となるプロジェクト構造とデータベースセットアップを実装した。

### 作成したファイル

#### 1. プロジェクト設定ファイル
- `.gitignore` - Python、DB、IDEなどの無視設定
- `requirements.txt` - fastmcp, pytest
- `pytest.ini` - pytestの設定（pythonpath指定）

#### 2. データベース関連
- `schema.sql` - データベーススキーマ定義
  - `projects` テーブル: プロジェクト管理
  - `discussion_topics` テーブル: 議論トピック（親子関係あり）
  - `discussion_logs` テーブル: 議論のやりとり記録
  - `decisions` テーブル: 決定事項記録
  - インデックス: 検索高速化のため各外部キーにインデックス設定

#### 3. ソースコード
- `src/__init__.py` - モジュール初期化
- `src/db.py` - データベース接続と操作関数
  - `get_db_path()`: DB パス取得（環境変数 or デフォルト）
  - `get_connection()`: DB 接続取得（Row factory 使用）
  - `init_database()`: スキーマ適用
  - `execute_query()`: SELECT クエリ実行
  - `execute_insert()`: INSERT クエリ実行（lastrowid 返却）
  - `row_to_dict()`: Row を辞書に変換

#### 4. テストコード
- `tests/test_db.py` - データベース機能のテスト（5テストケース）
  - 環境変数でのDB パス設定
  - デフォルトDB パス取得
  - データベース初期化
  - INSERT/SELECT 動作確認
  - Row factory 動作確認

### 技術選定

- **Python バージョン**: 3.12（FastMCP が 3.10 以上必須）
- **DB**: SQLite
- **DB 接続**: sqlite3（標準ライブラリ）
- **テスト**: pytest
- **MCP フレームワーク**: FastMCP

### 環境構築手順

```bash
# Python 3.12 のインストール（Homebrew）
brew install python@3.12

# 仮想環境作成
python3.12 -m venv venv

# 依存関係インストール
venv/bin/pip install -r requirements.txt

# テスト実行
venv/bin/pytest tests/ -v
```

### テスト結果

全5テストケースが PASS:
- `test_get_db_path_with_env` ✓
- `test_get_db_path_default` ✓
- `test_init_database` ✓
- `test_execute_insert_and_query` ✓
- `test_get_connection_returns_row_factory` ✓

## 問題と解決

### 1. FastMCP の Python バージョン要件
**問題**: システムの Python 3.9 では FastMCP（3.10以上必須）がインストールできない
**解決**: Homebrew で Python 3.12 をインストール

### 2. externally-managed-environment エラー
**問題**: システム Python への直接インストールが禁止されている
**解決**: venv（仮想環境）を使用

### 3. モジュールインポートエラー
**問題**: pytest が `src` モジュールを見つけられない
**解決**:
- `src/__init__.py` を作成
- `pytest.ini` で `pythonpath = .` を設定

## 次のステップ

PR #2 でプロジェクト管理API（`add-project`, `get-projects`）を実装する。
