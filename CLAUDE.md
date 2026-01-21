## 開発フロー規約

### 実装前の認識合わせ

**実装タスクを開始する前に、必ずユーザーと仕様の認識合わせを行う**

1. 関連トピックの決定事項を取得（`get_decisions(topic_id=...)`）
2. 決定事項一覧をユーザーに提示
3. 「この仕様で実装していい？」と確認
4. ユーザーのOKを得てから実装開始

**目的**: いきなり実装を始めて、仕様の認識ズレで手戻りが発生するのを防ぐ

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