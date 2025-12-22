# プロジェクトコンテキスト

## プロジェクト概要

Claude Codeの作業記録をDBに保存し、複数のClaude Codeエージェント間で協調作業を可能にするシステム。

## 主要な目的

1. **作業記録の永続化**: Claude Codeの実行ログ、意思決定、状態を記録
2. **複数エージェントの協調**: 同じタスクに複数のClaude Codeを当てて協調作業
3. **知識の蓄積と活用**: 議論から得られた「学び」をベクトル化してRAGで活用

## 重要な設計思想

### 1. next_stepsを書くべきでない

前のエージェントが生成した「次にやるべきこと」に頼ると思考停止する。次のエージェントは記録を見て自分で判断すべき。

### 2. 実行ログと意思決定は分離

- **task_logs**: やったこと、結果、事実（不変の記録）
- **decisions**: 方針、設計判断、理由（意思決定の根拠）

### 3. ステート管理はRedisで分離

`agent_status`（今何してる）は揮発性でOK。高速な状態共有に最適。

### 4. ベクトル化すべきは「学び」

単なる事実ではなく、議論のプロセスと結論の理由をベクトル化することで、LLMが賢くなっていく。

### 5. 監査ログはAPI層で強制

Claude Codeの善意に依存せず、API層で監査ログを強制的に記録する設計。

## アーキテクチャ方針

### 最終構成（更新: 2025-12-10）

```
Claude Code
    ↓ HTTP
自作API (Python + FastMCP)
    ↓
├── SQLite (tasks, task_logs, decisions)
└── (将来) ChromaDB (knowledgeのベクトル化)

※Redis (agent_status) は複数エージェント協調機能と共にスコープ外
```

### MCPを使わない理由

当初はSupabase MCPで手軽にDB操作する予定だったが、独自のドメインロジック（監査ログ強制、状態遷移制御、ベクトル化タイミング制御）が必要になり、MCPの汎用性では不十分と判断。

### データ層の役割分担

| レイヤー | 内容 | 性質 |
|---------|------|------|
| SQLite | tasks, task_logs, decisions | 永続、人間も参照可能 |
| mdファイル | knowledge（policies, lessons, references, facts） | 人間も編集可能、git管理 |
| (将来) ChromaDB | knowledgeのベクトル化 | LLMが参照して賢くなる |
| GitHub Issues | 設計議論・意思決定 | 人間も参加しやすい |

※Redis (agent_status) はスコープ外

## 決定事項（追加）

### ホスティング
- **ローカル環境**で動作させる（合意済み）

### プランモードの促進
- MCPサーバーのdescriptionに「このMCPはプランモードでの利用を推奨しています」と記載（合意済み）
- Claude Codeがツール参照時に自然に指示に従うことを期待

### session_id管理
- Claude Codeが自動生成する方式を採用（合意済み）
- セッション開始時にUUID生成（乱数ツール or 自力）
- MCPツール呼び出し時にsession_idを渡す
- 実装詳細は実装時に詰める

### knowledgeの保存方法
- **mdファイルで管理**（合意済み - 2025-12-10）
- 保存先: 環境変数`KNOWLEDGE_ROOT`で指定されたディレクトリ
  - 利点: Obsidian vaultとして使えば人間も見やすい
  - git管理可能（変更履歴を追える）

**ディレクトリ構造**:
```
${KNOWLEDGE_ROOT}/
  policies/                     # 設計原則・方針
    design/
      next-steps-antipattern.md

  lessons/                      # 経験から得た実践的な学び
    implementation/
    troubleshooting/

  references/                   # 技術資料・Webで調べたもの
    apis/
    databases/
    frameworks/

  facts/                        # 実測値・実験結果・調査事実
    errors/                     # エラー再現条件など
    resources/                  # 利用可能なリソース情報
```

**ファイル構造**:
```markdown
---
tags: [design-principles, antipattern, agents]
category: policies/design
created: 2025-12-10
updated: 2025-12-10
---

# next_stepsを書くべきでない理由

...
```

**タグ実装**: YAML frontmatter（Obsidian互換）

**検索方法**: MCPツールで検索機能を提供
```
mcp__knowledge__search
  input: { tags?: string[], keyword?: string, category?: string }
  output: { files: [...] }
```
- 内部でgrepやGlobを使って検索
- ユーザーはすでにClaude Desktop向けに類似機能を実装済み

**詳細設計**: 実装時に詰める（後回し）

### プロジェクト管理の追加（合意済み - 2025-12-10）

複数プロジェクトの議論・タスクを分離管理するため、projectsテーブルを追加。

- **projectsテーブル**: プロジェクト情報を管理
- **プロジェクトスコープ**: すべてのテーブルにproject_id追加（tasksとdiscussion_topics）
- **API変更**:
  - すべてのAPIにproject_id追加（引数の最初）
  - get-topicsを3つに分割（get-topics, get-decided-topics, get-undecided-topics）
  - 検索APIのproject_id必須化

### タスク管理システム（実装済み - 2025-12-23）

タスクのステータス管理とblocked時の自動トピック作成機能を実装。

- **MCPツール**:
  - `add_task`: 新しいタスクを追加
  - `get_tasks`: タスク一覧を取得（statusフィルタ可）
  - `update_task_status`: タスクステータスを更新
- **ステータス**: pending / in_progress / blocked / completed
- **blocked時の自動トピック作成**: blockedにするとdiscussion_topicsに自動でトピックが作成され、task.topic_idに紐付く

### スコープ外（後回し）
- 複数エージェント間の会話機能（Issue上でも代替可能 - 合意済み）
- ベクトル化機能（将来の拡張として別リポジトリで実装予定 - 合意済み）
- **Redisのagent_status機能**（合意済み - 2025-12-10）
  - 用途: 複数エージェント協調時の「今何してる」情報共有（ケースA）
  - 例: Claude Code Alphaが「タスク123のログイン機能実装中」を書き、Claude Code Betaがそれを読んで作業を調整
  - 理由: 複数エージェント協調は後回しなので、agent_statusも不要
  - 将来的に複数エージェント機能を実装する際に再検討

## データフロー（確定 - 2025-12-10）

```
1. ユーザー「〇〇機能を実装して」
   ↓
2. Claude Code: 既存タスク検索 or ユーザー確認
   ↓
3. Claude Code: タスク未存在 → MCPでtasks作成（task_id発行）
   ※ユーザー確認：タスク切らなくていい可能性もあるため
   ↓
4. Claude Code: プランモード → TodoWriteでタスク分解
   （各todoの「なぜ」がここで決まる）
   ↓
5. Claude Code: 各todoを実行
   ↓
6. TodoWrite(status=completed) → PostToolUseフック発火
   ↓
7. フック: 「今completeにしたタスクについて作業記録を行ってください」
   ↓
8. Claude Code: MCPツール呼び出し（log-completion）
   ↓
9. MCP: RDBに保存
```

### テーブル設計（更新 - 2025-12-10）

#### projectsテーブル（追加 - 2025-12-10）
```sql
CREATE TABLE projects (
  id INTEGER PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  asana_url TEXT,  -- AsanaプロジェクトタスクのURL
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**目的**: プロジェクトを管理。複数プロジェクトの議論・タスクを分離する。

**使用例:**
```
name: "claude-code-exterminal-memory"
description: "MCPサーバーを作るよ〜"
asana_url: "https://app.asana.com/0/..."
```

#### tasksテーブル（実装済み - 2025-12-23）
```sql
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending', 'in_progress', 'blocked', 'completed')),
  topic_id INTEGER REFERENCES discussion_topics(id) ON DELETE SET NULL,  -- blockedの時に関連する議論トピック
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**変更点（2025-12-23）**:
- `task_statuses`テーブルは廃止、`status`カラムにCHECK制約で直接管理
- `topic_id`を追加（blocked時に自動作成されるトピックへの参照）
- `completed_at`は廃止（シンプルさ優先）

**descriptionテンプレート:**
```markdown
## 目的
[なぜこのタスクをやるのか]

## 背景
[どういう文脈で発生したか]

## 完了条件
- [ ] [条件1]
- [ ] [条件2]

## 関連リソース
- GitHub Issue: [URL]
- ドキュメント: [URL]
- 関連ファイル: [path/to/file.ts]

## 備考
[その他、気をつけることや参考情報]
```

**タスク作成フロー:** ユーザーがタスクを依頼 → Claude Codeが確認質問（目的、背景、完了条件等）→ descriptionを生成 → MCPでtask作成

#### task_logsテーブル（未実装）

タスクの実行ログを記録するテーブル。将来的に実装予定。

**想定カラム**:
- task_id: 関連タスク
- session_id: セッション識別子
- summary: 作業概要
- purpose: 作業目的
- result: 作業結果
- issues: 発生した問題
- created_at: 作成日時

**原則**: RDBには事実のみ。改善提案（事実じゃない）、学んだこと（→ knowledgeへ）は記録しない。

#### discussion_topicsテーブル（更新 - 2025-12-10）
```sql
CREATE TABLE discussion_topics (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id),
  parent_topic_id INTEGER REFERENCES discussion_topics(id),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**目的**: 議論すべきトピックを管理。親子関係を持つことで、議論の文脈を保持。プロジェクトごとに分離。

**使用例:**
```
project_id: 1
title: "開発フローの詳細"
description: "プランモードの使い方、タスク分解の粒度、作業手順を決定する"
parent_topic_id: NULL  -- 最上位トピック
```

#### discussion_logsテーブル（追加 - 2025-12-10）
```sql
CREATE TABLE discussion_logs (
  id INTEGER PRIMARY KEY,
  topic_id INTEGER NOT NULL REFERENCES discussion_topics(id),
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**目的**: 議論のやりとりを記録（1レコード = 1やりとり）。

**使用例:**
```
topic_id: 1
content: "プランモードは設計議論フェーズでは不要。実装フェーズでTODO分解時に使用する。"
```

#### decisionsテーブル（更新 - 2025-12-10）
```sql
CREATE TABLE decisions (
  id INTEGER PRIMARY KEY,
  topic_id INTEGER REFERENCES discussion_topics(id),
  decision TEXT NOT NULL,      -- 決定内容
  reason TEXT NOT NULL,        -- 理由
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**目的**: 決定事項を記録。topicと紐付けることで、どの議論から生まれた決定かを追跡可能。

**使用例:**
```
topic_id: 2  -- "プランモードの使い方"
decision: "設計議論フェーズではプランモード不要。実装フェーズでtaskを実行する前にプランモードで具体的TODO分解を行う。"
reason: "設計議論では自由に発散→収束させたい。実装時は認識合わせが必要。"
```

**導入背景（dogfooding）**: このプロジェクトで設計中のシステムを、プロジェクト自体の議論記録に使用する。docs/での記録をDBに移行し、MCPツールで操作可能にする。

### 技術スタック（更新中 - 2025-12-10）

**アーキテクチャ:**
- モノリシック構成（1つのMCPサーバー）
- 将来的なマイクロサービス化は見送り（後でリプレイス可能）

**確定している技術選定:**
- **言語**: Python
- **MCPフレームワーク**: FastMCP
- **データベース**: SQLite（合意済み - 2025-12-10）
  - 現状のスコープ（単一エージェント、ローカル動作）に最適
  - セットアップが簡単（ファイルベース）
  - 将来的に必要になれば移行可能
- **DB接続**: sqlite3（Python標準ライブラリ）or SQLAlchemy（実装時に決定）

**選定理由:**
- FastMCPはMCPサーバー構築に特化しており、プロトコル実装が不要
- PostgreSQL/SQLite操作、ファイル操作はPythonの得意分野
- ローカル動作、単一エージェントのためパフォーマンスは問題にならない
- ユーザーはすでにClaude Desktop向けに類似機能を実装済み（流用可能）

**却下した選択肢:**
- Supabase（ラップ含む）: 今回のシンプルなユースケースには過剰
- マイクロサービス化: アーキテクチャ設計の複雑さを考慮し見送り

### ベクトル化の長期ビジョン（参考・将来）
- 調査結果、実測値（metrics）、洞察をmdファイルで保存（人間もAIも読む）
- アプリ内にLLMインスタンスを配置
- ドキュメント作成時に自動ベクトル化 → ベクトルDBへ
- エージェントが意識せず、アプリ内LLMが関連情報を自動取得してレスポンスに含める

## 開発フロー規約（合意済み - 2025-12-10）

### コミット規約
- **フォーマット**: Conventional Commits（`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`）
- **粒度**: 一言で描写できる程度

### ブランチ戦略
- **main直push**: pre-pushフックで防止
- **作業方法**: 原則としてgit worktreeを使用
- **ブランチ命名**: `feature/<feature-name>`, `fix/<issue-name>` など

### ドキュメント管理
- **保存場所**:
  - 決定事項、設計ドキュメント: `docs/` 配下
  - 調査結果、ナレッジ: `.specify/memory/` 配下
- **更新タイミング**:
  - ナレッジ: web_search実施後に更新要否を判断
  - 決定事項: 認識合わせ → ユーザーOK → 記録

### 決定事項の判定基準
- **定義**: エージェントが認識合わせ（「これであってる？」）→ ユーザーが承認（「OK」）→ 決定
- **認識合わせ時の必須チェック**:
  1. 論点の網羅性（見落としはないか）
  2. 前提の確認漏れはないか
  3. 性急な結論になっていないか

詳細は `/CLAUDE.md` を参照。

## 未決定事項・次回議論ポイント

**注意**: 最新の未決定事項はMCPツール（`get_undecided_topics`）で確認すること。このセクションは参考情報。

### 後回し（直近のやりたいこと完了後）

1. **ベクトルDB選定（ChromaDB vs pgvector）**
   - Chromaの自動埋め込み機能が魅力的
   - 将来的にはChromaを使いたい意向あり
   - SQLiteを使うためpgvectorは使えない（PostgreSQL専用）
   - ChromaDBを使う方向で検討予定
   - 参考資料: [chroma-vs-pgvector.md](references/databases/chroma-vs-pgvector.md)

### 高優先度

1. **PostToolUseフックの実装詳細**
   - フックスクリプトの書き方
   - プロンプトテンプレート
   - エラー時の挙動

2. **task_logsテーブルとMCPツールの実装**
   - log-completionツールの設計
   - session_id管理との連携

### 中優先度

3. **環境変数・設定管理**
   - DB接続情報
   - KNOWLEDGE_ROOT
   - その他設定項目

4. **エラーハンドリング・ロギング方針**
   - エラーをどう記録するか
   - ログレベル設計

### 実装済み（このドキュメントから削除予定の項目）

- ~~MCPツールの詳細設計~~（実装済み - 2025-12-23）
- ~~既存タスク検索の方法~~（search_topics, search_decisionsで実装済み）
- ~~インデックス設計~~（schema.sqlで実装済み）
- ~~DB接続ライブラリの選定~~（sqlite3標準ライブラリを採用）

## 参考資料

- [log.md](logs/2025-12-10.md): 設計議論の詳細ログ
- [chroma-vs-pgvector.md](references/databases/chroma-vs-pgvector.md): ChromaDBとpgvectorの比較調査（2025-12-10）
