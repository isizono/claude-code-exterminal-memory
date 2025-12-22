## 決定事項の判定基準と認識合わせプロセス

### 決定事項の判定基準

**決定事項とは**: エージェントが「これであってる？」「この理解で合ってる？」と認識合わせを行い、ユーザーが「OK」「合ってる」と承認したタイミングで確定する。

### 認識合わせ時の必須チェック項目

エージェントが認識合わせを行う際、必ず以下を自己チェックすること：

1. **論点の網羅性**: 認識合わせの話に上がっていない論点は何か？
   - 議論から派生する関連トピックを見落としていないか
   - 影響範囲を十分に考慮しているか

2. **前提の確認**: 前提の確認で漏れているものはないか？
   - ユーザーの発言の背後にある前提を正しく理解しているか
   - 技術的な制約や要件を見落としていないか

3. **性急な結論の回避**: 十分に発散的な議論を経たか？
   - 代替案を検討したか
   - トレードオフを明確にしたか

### フロー

```
1. エージェント: 提案・意見を提示
   ↓
2. 議論・検討（発散フェーズ）
   ↓
3. エージェント: 「〇〇という理解で合ってる？」
   ↓
   ★このタイミングで自己チェック★
   - 他に議論すべき論点はないか？
   - 前提の確認漏れはないか？
   - 性急な結論になっていないか？
   → 不足があれば追加で質問・提案
   ↓
4. ユーザー: 「OK」「合ってる」
   ↓
5. 決定事項としてMCPツールで記録（add_decision）
```

## 議論管理のワークフロー（MCPツール使用）

設計議論はMCPツール（claude-code-exterminal-memory）を使って管理する。

### 1. プロジェクトの特定

まず、作業対象のプロジェクトを特定する：

```python
# プロジェクト一覧を取得
projects = get_projects()

# 現在のプロジェクトのIDを確認
# 例: claude-code-exterminal-memory → project_id: 2
```

### 2. 設計議論の開始

新しい議論トピックを作成する：

```python
add_topic(
    project_id=2,
    title="○○機能の設計",
    description="議論の目的や背景",
    parent_topic_id=None  # 最上位トピックの場合
)
```

**子トピックを作る場合:**
```python
add_topic(
    project_id=2,
    title="詳細設計項目",
    description="...",
    parent_topic_id=親トピックのID
)
```

### 3. 議論のやりとり記録

AIとユーザーのやりとりを記録する：

```python
add_log(
    topic_id=トピックID,
    content="AI: 提案内容\nユーザー: フィードバック内容"
)
```

**記録タイミング:**
- 重要な議論の節目（提案→フィードバック）
- 複数のやりとりがあった場合、適宜まとめて記録
- 決定事項の前提となる議論は必ず記録

### 4. 決定事項の記録

認識合わせ → ユーザーOK → **即座に**記録する：

```python
add_decision(
    topic_id=関連トピックのID,
    decision="決定内容（何を決めたか）",
    reason="理由（なぜそう決めたか）"
)
```

**重要:**
- 後回しにせず、決定が確定した時点で記録すること
- セッションをまたぐ前に必ず記録を完了させる

### 5. 議論状況の確認

**未決定事項を確認:**
```python
get_undecided_topics(project_id=2)
get_undecided_topics(project_id=2, parent_topic_id=親ID)
```

**決定済み事項を確認:**
```python
get_decided_topics(project_id=2)
get_decisions(topic_id=トピックID)
```

**トピック構造を確認:**
```python
get_topics(project_id=2)  # 最上位トピック
get_topic_tree(project_id=2, topic_id=トピックID)  # ツリー全体
```

**検索:**
```python
search_topics(project_id=2, keyword="キーワード")
search_decisions(project_id=2, keyword="キーワード")
```

### 6. セッション開始時の状況把握

新しいセッション開始時は、MCPツールで最新状況を取得する：

1. プロジェクトを特定（get_projects）
2. 最上位トピックを確認（get_topics）
3. 未決定事項を確認（get_undecided_topics）
4. 必要に応じて特定トピックの詳細を取得（get_topic_tree, get_logs, get_decisions）

### 7. 目的

- 次セッションでの再開を容易にする
- 構造化された形で議論を追跡
- 決定事項の検索・参照を効率化
- 議論の経緯と現状を明確に保つ

## 開発フロー規約

### コミット規約

**フォーマット**: Conventional Commits形式を使用する

```
<type>: <subject>

<body>（任意）
```

**タイプ一覧**:
- `feat:` - 新機能の追加
- `fix:` - バグ修正
- `docs:` - ドキュメントのみの変更
- `refactor:` - リファクタリング（機能変更なし）
- `test:` - テストの追加・修正
- `chore:` - ビルド、依存関係、その他の雑務

**粒度**: 一言で描写できる程度にまとめる

**例**:
```
feat: tasksテーブルのスキーマを実装
docs: ChromaDB vs pgvectorの調査結果を追加
fix: session_id生成時のUUID形式を修正
```

### ブランチ戦略

**main直push禁止**: pre-pushフックで防止する

**作業方法**: 原則としてgit worktreeを使用する

```bash
# 新しい作業ツリーを作成（.trees/配下に格納）
git worktree add .trees/feature-x feature/feature-x

# 作業完了後
git worktree remove .trees/feature-x

# worktree一覧を確認
git worktree list
```

**配置ルール**: worktreeは必ず`.trees/`ディレクトリ配下に作成する（`.gitignore`に登録済み）

**ブランチ命名規則**: `feature/<feature-name>`, `fix/<issue-name>` など

### ドキュメント管理

**保存場所の役割分担:**

| 内容 | 保存場所 | ツール |
|------|---------|--------|
| 決定事項、議論ログ、トピック | MCPツール | add_decision, add_log, add_topic |
| 参考資料（web検索結果、技術調査） | `docs/references/` | Write/Edit |
| 未決定事項の追跡 | MCPツール | get_undecided_topics |

**更新タイミング**:

1. **ナレッジ更新**: web_searchを実施した後、更新要否を判断する
   - 新しい知見が得られた場合は `docs/references/` などに保存
   - 既存ドキュメントに追記すべき情報があれば更新

2. **決定事項更新**: ユーザーとエージェントで合意形成が行われるたびに更新
   - 認識合わせ → ユーザーOK → **MCPツールで記録**（add_decision）

**ドキュメントテンプレート**: 後日話し合って決定する
- トピックを取り上げる際、ユーザーに軽く内容を説明する