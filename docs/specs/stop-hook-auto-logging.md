# Stopフックによる会話記録の自動化 - 仕様書

## 1. 概要

### 目的
- 毎ターンの会話（ユーザー発言 + AI応答）を自動でログに記録する
- エージェントが記録を忘れる問題を解決する
- トピック変更時に決定事項の記録漏れを防ぐ

### 背景
- 従来: CLAUDE.mdにadd_log呼び出しを指示 → 忙しいと忘れがち
- 新方式: Stopフックで強制的に記録 + メタタグ出力を強制

## 2. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code セッション                     │
│                                                             │
│  ユーザー発言 → AI応答 → Stop発火                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     Stopフック (Bash)                        │
│                                                             │
│  入力JSON:                                                  │
│  - session_id                                               │
│  - transcript_path                                          │
│  - stop_hook_active                                         │
│                                                             │
│  処理フロー:                                                 │
│  1. stop_hook_active=true → approve（無限ループ防止）        │
│  2. メタタグチェック → なければblock                          │
│  3. トピック変更チェック → 前topicにdecisionなければblock     │
│  4. approve + バックグラウンドでログ記録                      │
└─────────────────┬───────────────────────────────────────────┘
                  │ バックグラウンド
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  ログ記録処理 (Python)                        │
│                                                             │
│  1. transcriptから直近1リレーを抽出                          │
│  2. claude --model haiku で要約                             │
│  3. service層でadd_log()                                    │
└─────────────────────────────────────────────────────────────┘
```

## 3. メタタグ仕様

### フォーマット（本番運用時）
```html
<!-- [meta] project: {project_name} (id: {project_id}) | topic: {topic_title} (id: {topic_id}) -->
```

**注**: HTMLコメント形式で出力することで、ユーザーには見えないがhookでパース可能。

### ルール
- AIは毎ターンの応答の最後にメタタグを出力する
- Stopフックでメタタグがなければblockされる
- トピックが変わった場合は新しいtopic_idを出力する

## 4. 1リレーの定義

### 判定ロジック

| エントリタイプ | type | toolUseResult |
|--------------|------|---------------|
| 人間のユーザー発言 | `user` | なし |
| ツール結果 | `user` | あり |
| AI応答 | `assistant` | - |

### 1リレーの範囲
```
[Human User] → [Assistant]* → ([Tool Result] → [Assistant])* → [次のHuman User]
```

人間のユーザー発言から、次の人間のユーザー発言の直前までが1リレー。

## 5. Stopフック処理詳細

### 入力JSON（stdin）
```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../session.jsonl",
  "stop_hook_active": true
}
```

### 処理フロー

```bash
#!/bin/bash
INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')

# 1. 無限ループ防止
if [ "$STOP_ACTIVE" = "true" ]; then
  echo '{"decision": "approve"}'
  exit 0
fi

# 2. メタタグチェック
LAST_ASSISTANT=$(tac "$TRANSCRIPT_PATH" | grep -m1 '"type":"assistant"')
if ! echo "$LAST_ASSISTANT" | grep -q '\[meta\]'; then
  echo '{"decision": "block", "reason": "応答の最後に [meta] タグを出力してください"}'
  exit 0
fi

# 3. トピック変更チェック
CURRENT_TOPIC=$(echo "$LAST_ASSISTANT" | grep -oP 'topic:.*id: \K\d+')
PREV_TOPIC=$(cat /tmp/claude_prev_topic_${SESSION_ID} 2>/dev/null || echo "")

if [ -n "$PREV_TOPIC" ] && [ "$PREV_TOPIC" != "$CURRENT_TOPIC" ]; then
  # 前のトピックにdecisionがあるかチェック
  HAS_DECISION=$(python3 /path/to/check_decision.py "$PREV_TOPIC")
  if [ "$HAS_DECISION" = "false" ]; then
    echo '{"decision": "block", "reason": "トピックが変わりました。前のトピック(id='$PREV_TOPIC')に決定事項を記録してください"}'
    exit 0
  fi
fi

# 4. 現在のトピックを保存
echo "$CURRENT_TOPIC" > /tmp/claude_prev_topic_${SESSION_ID}

# 5. approve + バックグラウンドでログ記録
python3 /path/to/record_log.py "$TRANSCRIPT_PATH" "$CURRENT_TOPIC" &

echo '{"decision": "approve"}'
exit 0
```

## 6. ログ記録スクリプト (Python)

```python
#!/usr/bin/env python3
import sys
import json
import subprocess

def extract_last_relay(transcript_path: str) -> list[dict]:
    """直近1リレーを抽出"""
    entries = []
    with open(transcript_path) as f:
        for line in f:
            entries.append(json.loads(line))

    # 後ろから走査して直近1リレーを取得
    relay = []
    found_human = False
    for entry in reversed(entries):
        if entry.get('type') in ('file-history-snapshot', 'system', 'summary'):
            continue

        is_human = entry.get('type') == 'user' and 'toolUseResult' not in entry

        if is_human:
            if found_human:
                break  # 前のリレーに到達
            found_human = True

        relay.insert(0, entry)

    return relay

def summarize_with_haiku(relay: list[dict]) -> str:
    """Haikuで要約"""
    # リレーをテキスト化
    text = json.dumps(relay, ensure_ascii=False, indent=2)

    prompt = f"""以下の会話を要約してください。
形式: 「ユーザー: 〇〇と言った / AI: △△と考え、□□と応答した」

{text}"""

    result = subprocess.run(
        ['claude', '--model', 'haiku', '-p', prompt],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def save_log(topic_id: int, content: str):
    """DBに保存"""
    sys.path.insert(0, '/path/to/claude-code-exterminal-memory')
    from src.services import discussion_log_service
    discussion_log_service.add_log(topic_id, content)

if __name__ == '__main__':
    transcript_path = sys.argv[1]
    topic_id = int(sys.argv[2])

    relay = extract_last_relay(transcript_path)
    summary = summarize_with_haiku(relay)
    save_log(topic_id, summary)
```

## 7. 設定ファイル

### rulesファイル（メタタグ出力ルール）

`~/.claude/rules/meta-tag.md`:
```markdown
# メタタグ出力ルール

毎ターンの応答の最後に、以下の形式でメタタグを出力すること：

**[meta]**
- project: {プロジェクト名} (id: {プロジェクトID})
- topic: {トピックタイトル} (id: {トピックID})

トピックが変わる場合は新しいIDを出力する。
```

### hooks設定

`.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/stop_hook.sh"
          }
        ]
      }
    ]
  }
}
```

## 8. 決定事項一覧

| # | 決定事項 | 理由 |
|---|---------|------|
| 1 | 実装方式: Stopフック + claude CLI (haiku) + transcript tail | Stopは会話の区切りで発火、transcript_pathが入力に含まれる、API不要 |
| 2 | ログ粒度: 直近1リレー分 | 細かすぎず粗すぎず適切な単位 |
| 3 | 1リレーの定義: type='user' かつ toolUseResult なし から次まで | transcript分析の結果、この判定が確実 |
| 4 | topic_id特定: AIがメタタグとして出力 | hookから現在のトピックを特定する手段がないため |
| 5 | メタタグ強制: なければblock | CLAUDE.mdだけだと忘れる可能性があるため |
| 6 | トピック変更時: 前topicにdecisionなければblock | 議論の区切りでdecision忘れを防ぐ。警告だけだとスルーされる可能性があるため一旦厳しめで実装 |
| 7 | メタタグはHTMLコメント形式で出力 | ユーザーにはノイズになるため非表示にしつつ、hookでパース可能な形式を維持 |
| 8 | SessionStartフックで未決定トピックをN件取得してAIに渡す | 最初にコンテキストを把握。ユーザーが関係ない話を始めたら前の未決定トピックはサンクコストとして放置 |
| 9 | get_startup_context MCPツールを新規作成 | SessionStartフック用。全プロジェクト横断で未決定トピックをlimit件取得。project_idは引数に取らない（1リポジトリに複数プロジェクトが存在しうるため自動推測不可） |

## 9. 実装タスク

### Stopフック関連
- [ ] Stopフックスクリプト (`stop_hook.sh`)
- [ ] ログ記録スクリプト (`record_log.py`)
- [ ] decision存在チェックスクリプト (`check_decision.py`)
- [ ] rulesファイル (`~/.claude/rules/meta-tag.md`)
- [ ] settings.json への hooks 設定追加
- [ ] Stopフック自動ログ記録のテスト

### SessionStartフック関連
- [ ] get_startup_context MCPツールの実装
- [ ] SessionStartフックの実装

## 10. SAレビュー指摘事項（要対応）

- **macOS互換性**: `grep -oP` がmacOSの標準grepで動かない → 実装時にPythonに統一するか、GNU grep前提とするか検討
- **transcript解析のパフォーマンス**: 大きなファイルの全読み込みは非効率 → tail相当で末尾だけ読む最適化を検討
- **バックグラウンド処理の失敗ハンドリング**: Haiku呼び出し失敗時のリトライ等が未定義
