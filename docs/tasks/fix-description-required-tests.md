# タスク: descriptionフィールド必須化に伴うテスト修正

## 決定事項（2025-12-11 認識合わせ完了）

### 現在の矛盾
- **実装側（修正済み）**: スキーマ、サービス層、MCPツールすべてで `description` が必須
- **テスト側（未修正）**: `add_project()`, `add_topic()` の呼び出しで `description` を省略している箇所が多数（約55箇所）
- **結果**: 47件のテスト失敗（TypeError、IntegrityError）

### 正しい姿
すべての層で `description` が必須であることが一貫している状態：
1. スキーマ: `description TEXT NOT NULL` ✅
2. サービス層: `description: str` ✅
3. MCPツール: `description: str` ✅
4. テストコード: すべての呼び出しで `description` を明示的に指定 ❌（要修正）
5. 全70テストがPASS ❌（要修正）

### 作業方針
- 既存テストの修正のみ（新規テスト追加なし）
- テスト修正作業はサブエージェントに委譲

---

## 現在の状態（2025-12-11時点）

### 完了したこと

1. **Python 3.12への固定**
   - `.python-version` 追加
   - `pyproject.toml` 追加（`requires-python = ">=3.12"`）

2. **descriptionフィールドを必須化**
   - `schema.sql`: `description TEXT NOT NULL` (DEFAULTなし)
   - `src/services/project_service.py`: `description: str` (必須)
   - `src/services/topic_service.py`: `description: str` (必須)
   - `src/main.py`: MCPツールの引数を`description: str`に変更
   - API仕様書: `description` ✓ (必須) - すでに正しい

### 問題点

テストが47件失敗/エラー（20 failed, 27 errors）

**主な原因:**
- 既存のテストコードが古いAPI（descriptionオプショナル）を想定している
- `add_project(name="test")`のようにdescriptionを省略している呼び出しが多数ある
- `add_topic(project_id=1, title="test")`のようにdescriptionを省略している呼び出しが多数ある

## 正しい姿（目標状態）

### 1. スキーマ定義
```sql
-- schema.sql
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT NOT NULL,  -- ✓ 必須、DEFAULTなし
  asana_url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discussion_topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id),
  parent_topic_id INTEGER REFERENCES discussion_topics(id),
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,  -- ✓ 必須、DEFAULTなし
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2. サービス層API
```python
# src/services/project_service.py
def add_project(
    name: str,
    description: str,  -- ✓ 必須
    asana_url: Optional[str] = None,
) -> dict:
    ...

# src/services/topic_service.py
def add_topic(
    project_id: int,
    title: str,
    description: str,  -- ✓ 必須
    parent_topic_id: Optional[int] = None,
) -> dict:
    ...
```

### 3. MCPツールAPI
```python
# src/main.py
@mcp.tool()
def add_project(
    name: str,
    description: str,  -- ✓ 必須
    asana_url: Optional[str] = None,
) -> dict:
    ...

@mcp.tool()
def add_topic(
    project_id: int,
    title: str,
    description: str,  -- ✓ 必須
    parent_topic_id: Optional[int] = None,
) -> dict:
    ...
```

### 4. API仕様書
```markdown
# docs/api-specification.md

### add-project
| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `name` | string | ✓ | プロジェクト名（ユニーク） |
| `description` | string | ✓ | プロジェクトの説明 |  -- ✓ 必須
| `asana_url` | string | | AsanaプロジェクトタスクのURL |

### add-topic
| 名前 | 型 | 必須 | 説明 |
|------|------|------|------|
| `project_id` | integer | ✓ | プロジェクトID |
| `title` | string | ✓ | トピックのタイトル |
| `description` | string | ✓ | トピックの説明 |  -- ✓ 必須
| `parent_topic_id` | integer | | 親トピックのID |
```

### 5. テスト
**全70テストがPASS** (現在: 23 passed, 20 failed, 27 errors)

## 次の作業（優先順位順）

### ステップ1: テストコードの修正

#### 1-1. add_project呼び出しの修正

修正対象のテストファイル:
- `tests/integration/test_edge_cases.py`
- `tests/integration/test_mcp_tools.py`
- `tests/unit/test_search_service.py`
- `tests/unit/test_topic_read.py`
- `tests/unit/test_topic_write.py`

**修正パターン:**
```python
# 修正前
add_project(name="test-project")

# 修正後
add_project(name="test-project", description="Test project description")
```

#### 1-2. add_topic呼び出しの修正

修正対象のテストファイル:
- `tests/integration/test_edge_cases.py`
- `tests/unit/test_search_service.py`
- `tests/unit/test_topic_read.py`
- `tests/unit/test_topic_write.py`

**修正パターン:**
```python
# 修正前
add_topic(project_id=test_project, title="Test Topic")

# 修正後
add_topic(project_id=test_project, title="Test Topic", description="Test topic description")
```

#### 1-3. バリデーションテストの修正

以下のテストケースを修正または削除:
- `test_add_project_minimal` - descriptionが必須なので「必須項目のみ」の意味が変わる
- `test_add_project_with_required_description_at_api_level` - 既に必須なので不要
- `test_add_topic_with_required_description_at_api_level` - 既に必須なので不要

### ステップ2: 新しいテストケースの追加（オプション）

descriptionが必須であることを確認するテスト:
```python
def test_add_project_missing_description_raises_error():
    """descriptionが指定されていない場合、TypeErrorが発生する"""
    with pytest.raises(TypeError):
        add_project(name="test-project")

def test_add_topic_missing_description_raises_error():
    """descriptionが指定されていない場合、TypeErrorが発生する"""
    with pytest.raises(TypeError):
        add_topic(project_id=1, title="Test Topic")
```

### ステップ3: DB初期化の修正

`tests/test_db.py`と`tests/unit/test_db.py`の以下のテストを修正:
- `test_get_connection_returns_row_factory`

**エラー内容:**
```
sqlite3.IntegrityError: NOT NULL constraint failed: projects.description
```

**修正方法:**
テストコード内でプロジェクトを作成している箇所でdescriptionを追加する。

## 作業の進め方

1. **まず`tests/unit/test_db.py`と`tests/test_db.py`を修正**
   - これらは基本的なDBテストなので最優先

2. **次に`tests/unit/test_topic_write.py`を修正**
   - 書き込み系のテストを先に修正

3. **`tests/unit/test_topic_read.py`を修正**
   - 読み取り系のテストを修正

4. **`tests/unit/test_search_service.py`を修正**
   - 検索系のテストを修正

5. **`tests/integration/`配下を修正**
   - 統合テストを最後に修正

## 期待される成果

- ✅ 全70テストがPASS
- ✅ descriptionフィールドが必須として正しく機能
- ✅ API仕様書と実装が完全に一致
- ✅ Python 3.12で動作確認完了

## 関連ファイル

- `schema.sql` - ✅ 修正済み
- `src/services/project_service.py` - ✅ 修正済み
- `src/services/topic_service.py` - ✅ 修正済み
- `src/main.py` - ✅ 修正済み
- `.python-version` - ✅ 追加済み
- `pyproject.toml` - ✅ 追加済み
- `.gitignore` - ✅ .venv/追加済み
- `tests/**/*.py` - ❌ 修正必要（次の作業）

## 注意事項

- descriptionは空文字列でもOK（NOT NULLだが値は自由）
- テスト用のdescriptionは簡潔に（例: "Test description"）
- 既存のテストロジックは変更しない（description引数を追加するだけ）
