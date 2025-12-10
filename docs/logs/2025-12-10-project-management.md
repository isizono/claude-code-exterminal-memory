# 2025-12-10 議論ログ：プロジェクト管理機能の追加

## セッション概要

- **日付**: 2025-12-10
- **参加者**: ユーザー、Claude（エージェント）
- **トピック**: API仕様のレビューとプロジェクト管理機能の設計
- **成果**: テーブル設計とAPI仕様の全面改訂

---

## 発見した問題

### 1. API仕様のレビューコメント対応

PRに対して5つのレビューコメントを受領：

1. **add-logの例が不明瞭**: 「1やりとり」の粒度が分かりづらい
2. **get-topicsの設計が複雑**: `include_tree`のboolではなく、別APIに分けるべき
3. **get-logsのページネーション不足**: `limit`だけでは101件目以降取得できない
4. **get-decisionsの全件検索**: 全件検索は不要
5. **検索の部分一致パフォーマンス**: 将来的にベクトル検索への移行を検討

### 2. より重大な問題：プロジェクト管理の欠如

API仕様をレビュー中、**get周りのIDが必須じゃない**問題を発見：
- `get-topics(parent_topic_id=null)` で最上位全件取得 → プロジェクトまたがると爆発
- `get-topic-tree(topic_id=null)` で全ツリー → 同じく爆発

この問題を掘り下げた結果、**複数プロジェクトを区別する手段が一切ない**という根本的な設計欠陥が判明。

---

## 議論の経緯

### フェーズ1: レビューコメントへの対応検討

**AI提案**: レビューコメントに基づいて修正方針を提示
- add-logの例を対話形式に変更
- get-topicsを2つのAPIに分割（get-topics, get-topic-tree）
- ページネーション用の`start_id`追加
- get-decisionsの`topic_id`必須化
- 検索APIに`limit`追加

**ユーザー承認**: 全て了承

### フェーズ2: プロジェクト管理の必要性に気づく

**ユーザー指摘**: 「get周りでidに必須ついてないのやばくない？」

**AI分析**:
- `get-topics`は`parent_topic_id=null`で全件取得可能
- `get-topic-tree`は`topic_id=null`で全ツリー取得可能
- 複数プロジェクトの議論が混在すると爆発する

**AI提案**: 3つの解決策を提示
1. projectsテーブル + project_id（正規化）
2. tagsで緩く管理（柔軟だが検索遅い）
3. project_nameカラム（シンプルだがタイポリスク）

**ユーザー**: tasksテーブルの`asana_url`カラムを思い出す
→ 「Asanaはprojectに紐づけられるべき」

### フェーズ3: テーブル設計の詳細を詰める

**合意形成**:
- **projectsテーブル**: プロジェクト情報を管理
- **asana_url**: projectsテーブルに配置（タスクベースのURL）
- **tasksテーブル**: asana関連削除、project_idのみ追加

**ユーザー提案**: 「statusはテーブルごと切り出すか」
→ **task_statusesテーブル**を追加し、正規化

**ユーザー提案**: 「VARCHAR長さは255で」
→ TEXT→VARCHAR(255)に変更（パフォーマンス改善）

### フェーズ4: トピック取得APIの設計

**ユーザー提案**: 「決定済み/未決定でフィルターできるように第三引数にbool」

**AI提案**: SQLの実装イメージを提示（INNER JOIN vs LEFT JOIN）

**ユーザー判断**: 「関数ごと切り出そう！先生に怒られそう！」
→ **3つのAPIに分割**:
- `get-topics`: 全トピック
- `get-decided-topics`: 決定済みのみ
- `get-undecided-topics`: 未決定のみ

**確認**: get-topic-treeは分けない（topic_idの指定をするから）

---

## 決定事項

### テーブル設計

#### 新規追加

1. **projectsテーブル**
```sql
CREATE TABLE projects (
  id INTEGER PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  asana_url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

2. **task_statusesテーブル**
```sql
CREATE TABLE task_statuses (
  id INTEGER PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE
);

INSERT INTO task_statuses (name) VALUES ('active'), ('completed'), ('cancelled');
```

#### 既存テーブルの変更

3. **tasksテーブル**
- `project_id`追加（NOT NULL）
- `status`→`status_id`に変更（外部キー）
- `asana_url`削除
- `title`: TEXT→VARCHAR(255)

4. **discussion_topicsテーブル**
- `project_id`追加（NOT NULL）
- `title`: TEXT→VARCHAR(255)

### API仕様

#### 新規追加API

1. **add-project**: プロジェクト追加
2. **get-projects**: プロジェクト一覧取得
3. **get-decided-topics**: 決定済みトピック取得
4. **get-undecided-topics**: 未決定トピック取得

#### 既存APIの変更

5. **全APIに`project_id`追加**: 引数の最初に配置
6. **get-topics**: `parent_topic_id`はオプション（1階層のみ）
7. **get-topic-tree**: `topic_id`必須、分割なし
8. **get-logs**: `start_id`追加（ページネーション）、limit=30
9. **get-decisions**: `topic_id`必須、全件検索削除
10. **search-topics/decisions**: `project_id`必須化、`limit`追加

### 設計原則

- **プロジェクト分離**: 複数プロジェクトの議論・タスクを分離管理
- **正規化**: ステータスはテーブル化
- **パフォーマンス**: TEXT→VARCHAR(255)で改善
- **引数順序**: project_idを最初に配置（最重要パラメータ）

---

## 却下した選択肢

1. **タグによる管理**: 柔軟だが検索が遅い、命名規則が必要
2. **project_nameカラム（正規化しない）**: タイポリスク、リネーム時の全更新
3. **全件検索**: 「トピックから探索して欲しい」
4. **get-topic-treeの分割**: topic_idの指定があるから不要

---

## 学んだこと

1. **API設計は使い方から逆算する**: 「全件取得できてしまう」という実装可能性ではなく、「全件取得すべきか」という使い方で判断
2. **スコープの重要性**: MCPサーバーは複数プロジェクトで使うという前提を早期に考慮すべきだった
3. **正規化のタイミング**: ステータスのような固定値はテーブル化することで、将来の拡張に対応しやすい
4. **関数分割の判断**: 複雑なif分岐よりも、明確な責務を持つ複数の関数の方が保守性が高い

---

## 残論点・次回議論ポイント

### 実装前に決めること

1. **DB接続ライブラリ**: sqlite3 vs SQLAlchemy（今回は「sqlite3でいく」と決定済み）
2. **MCPツールの詳細設計**: エラーハンドリング、バリデーション
3. **PostToolUseフック**: 実装詳細

### 今後検討すること

1. **インデックス設計**: パフォーマンス最適化
2. **マイグレーション方針**: スキーマ変更時の対応
3. **ベクトル検索への移行**: LIKE検索からの移行タイミング

---

## 次のステップ

1. **PR承認待ち**: https://github.com/isizono/claude-code-exterminal-memory/pull/2
2. **実装開始**:
   - SQLiteデータベース作成
   - MCPサーバー実装（FastMCP）
   - テスト作成（pytest）
3. **初期データ投入**: project_id=1として「claude-code-exterminal-memory」を登録
4. **動作確認**: MCPツールを実際に使って議論記録を試す

---

## 参考資料

- [API仕様書](../api-specification.md)
- [プロジェクトコンテキスト](../project-context.md)
- [PR #2](https://github.com/isizono/claude-code-exterminal-memory/pull/2)
