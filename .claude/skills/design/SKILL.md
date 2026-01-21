---
name: design
description: 設計タスクをするときに発動。方針・仕様を決め、実装に必要な決定事項を揃える。Planの作成や、実装に着手する前に使用するようにしてください。
---

# 設計フェーズ Skill

## 目的

議論フェーズで明確になったWhat/Why/Scopeをもとに、具体的な方針・仕様を決定し、実装に必要な決定事項を揃える。

## 開始前チェック（必須）

**このSkillを実行する前に、必ず以下を確認する：**

1. 関連する `[議論]` タスクを探す
2. そのタスクに紐づくdecision（What/Why/Scope）があるか確認
3. **What/Why/Scopeを確認できるdecisionがない場合**:
   - ユーザーに「まず議論が必要」と伝える
   - 議論フェーズへ誘導する
   - **このSkillの処理は中断する**

```
例: 「トピック検索機能」の設計を始める場合

1. タスク一覧から [議論] タスクを探す
   get_tasks(project_id=2)
   → { tasks: [{ id: 38, title: "[議論] トピック検索機能の要件整理", topic_id: 85, ... }] }

2. そのタスクに紐づくトピックの決定事項を確認
   get_decisions(topic_id=85)
   → {
       decisions: [{
         decision: "【What】トピックをキーワードで検索できるようにする
                    【Why】トピック数が増えると目的のトピックを見つけにくくなるため
                    【Scope】title/descriptionの部分一致検索。全文検索や曖昧検索はやらない
                    【Acceptance】「hooks」で検索したらhooks関連のトピックが出てくる",
         reason: "..."
       }]
     }

3. What/Why/Scope/Acceptanceが揃っている → 設計フェーズへ進める
   ※ 不足している場合は議論フェーズへ戻す
```

## 開始時のアクション

開始前チェックをパスしたら：

1. `[設計]` タスクを作成する
2. 議論フェーズのdecisionを確認し、前提を共有する

```
例: 「トピック検索機能」の設計を開始

1. 設計タスクを作成
   add_task(
       project_id=2,
       title="[設計] トピック検索機能の方針決定",
       description="議論フェーズで決まったWhat/Why/Scope/Acceptanceをもとに、How/Interface/Edge cases/Verificationを決める"
   )

2. 議論フェーズの決定事項をユーザーに共有
   「議論フェーズで以下が決まってるね：
   - What: トピックをキーワードで検索できるようにする
   - Why: トピック数が増えると目的のトピックを見つけにくくなるため
   - Scope: title/descriptionの部分一致検索。全文検索や曖昧検索はやらない
   - Acceptance: 「hooks」で検索したらhooks関連のトピックが出てくる

   この前提で設計進めていい？」
```

## 完了条件

実装に必要な決定事項が揃っていること：

- **How**: どう実現するか（技術選定、アーキテクチャ、アプローチ）
- **Interface**: 外部とのやり取り（API、UI、データ形式など）
- **Edge cases**: 考慮すべきエッジケース・エラーハンドリング
- **Verification**: 最低限の動作保証項目

### 具体例

```
例: 「トピック検索機能」の設計

前提（議論フェーズで決定済み）:
- What: トピックをキーワードで検索できるようにする
- Why: トピック数が増えると目的のトピックを見つけにくくなるため
- Scope: title/descriptionの部分一致検索。全文検索や曖昧検索はやらない
- Acceptance: 「hooks」で検索したらhooks関連のトピックが出てくる

【How】
- SQLiteのLIKE句を使用（%keyword%形式）
- 検索対象カラム: title, description
- 大文字小文字: SQLiteデフォルトのCOLLATE NOCASEで区別しない
- 検索ロジック: titleまたはdescriptionのいずれかにマッチすればヒット
- 結果の並び順: created_at DESC（新しい順）

【Interface】
- MCPツール: search_topics(project_id: int, keyword: str, limit: int = 30)
- 戻り値: { topics: [{ id, title, description, parent_topic_id, created_at }, ...] }
- エラー時: MCPの標準エラー形式で返す

【Edge cases】
- keywordが空文字 → エラーを返す（全件取得はget_topicsを使う）
- keywordが1文字 → 許可する（ただし結果が多くなる可能性あり）
- 該当なし → 空配列を返す（エラーではない）
- keywordに%や_が含まれる → エスケープしてリテラル検索する
- project_idが存在しない → 空配列を返す（エラーではない）

【Verification】
- 正常系
  - 「hook」で検索 → 「Stopフック実装」「PostToolUseフック」等がヒット
  - 「HOOK」で検索 → 同じ結果（大文字小文字無視の確認）
  - descriptionに「自動記録」を含むトピック → 「自動記録」で検索してヒット
- 異常系
  - 空文字で検索 → エラーが返る
  - 存在しないproject_id=9999で検索 → 空配列が返る
- エッジケース
  - 「%」で検索 → %を含むトピックのみヒット（ワイルドカードとして解釈されない）
  - limit=1で検索 → 1件だけ返る
```

## エージェントの振る舞い

### 基本姿勢

**トレードオフを明示**して、ユーザーに選ばせる。エージェントが勝手に決めない。

### やること

- **代替案を提示する**: 「A案とB案があるけど、どっちがいい？」
- **トレードオフを説明する**: 「A案は〇〇がメリットだけど、△△がデメリット」
- **影響範囲を確認する**: 「これ変えると、〇〇にも影響あるけど大丈夫？」
- **抜け漏れを指摘する**: 「〇〇のケース考慮してなくない？」

### 根拠のルール

**1次情報ベース**で判断する。

- 公式ドキュメント・ベストプラクティスや、実際のコードベースなどを根拠にする
- 信頼度の高いソースを示せないのは原則NG

## 成果物

設計で決まった内容を、トピックに紐づく決定事項（decision）として記録する。

```
例: 「トピック検索機能」の設計完了時

add_decision(
    topic_id=85,
    decision="""【How】
- SQLiteのLIKE句を使用（%keyword%形式）
- 検索対象カラム: title, description
- 大文字小文字: SQLiteデフォルトのCOLLATE NOCASEで区別しない
- 検索ロジック: titleまたはdescriptionのいずれかにマッチすればヒット
- 結果の並び順: created_at DESC（新しい順）

【Interface】
- MCPツール: search_topics(project_id: int, keyword: str, limit: int = 30)
- 戻り値: { topics: [{ id, title, description, parent_topic_id, created_at }, ...] }
- エラー時: MCPの標準エラー形式で返す

【Edge cases】
- keywordが空文字 → エラーを返す（全件取得はget_topicsを使う）
- keywordが1文字 → 許可する（ただし結果が多くなる可能性あり）
- 該当なし → 空配列を返す（エラーではない）
- keywordに%や_が含まれる → エスケープしてリテラル検索する
- project_idが存在しない → 空配列を返す（エラーではない）

【Verification】
- 正常系
  - 「hook」で検索 → 「Stopフック実装」「PostToolUseフック」等がヒット
  - 「HOOK」で検索 → 同じ結果（大文字小文字無視の確認）
  - descriptionに「自動記録」を含むトピック → 「自動記録」で検索してヒット
- 異常系
  - 空文字で検索 → エラーが返る
  - 存在しないproject_id=9999で検索 → 空配列が返る
- エッジケース
  - 「%」で検索 → %を含むトピックのみヒット（ワイルドカードとして解釈されない）
  - limit=1で検索 → 1件だけ返る""",
    reason="SQLiteのLIKE句はシンプルで十分な性能。全文検索エンジン（FTS5等）は今回のスコープ外。大文字小文字の区別はユーザー体験として不要と判断。"
)
```

## フェーズ移行

完了条件を満たしたら、ユーザーに確認を取って実装フェーズへ移行する。