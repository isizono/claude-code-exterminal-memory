# Claude Code Hook: ツール使用履歴の取得方法

## 調査日

2024-12-24

## 調査目的

エージェントのレスポンス生成完了時（Stopイベント）で、その生成過程で使用されたツールの一覧を取得できるか調査する。

## 結論

**可能**（transcript_pathの解析、またはPostToolUseフラグパターンで実現可能）

## 詳細

### 方法1: transcript_path解析（推奨）

Stopイベントで以下の情報が渡される：

```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
  "permission_mode": "default",
  "hook_event_name": "Stop",
  "stop_hook_active": true
}
```

`transcript_path`のJSONLファイルを解析することで、使用したツール一覧を取得できる。

```bash
#!/bin/bash
input=$(cat)
transcript_path=$(echo "$input" | jq -r '.transcript_path')

# transcriptファイルを解析してツール一覧を抽出
jq -r '.[] | select(.type == "tool_use") | .name' "$transcript_path" | sort | uniq
```

### 方法2: PostToolUse + Stopフラグパターン

PostToolUseでフラグファイルに追記し、Stopで参照する。

**PostToolUse hook:**
```bash
#!/bin/bash
input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')
session_id=$(echo "$input" | jq -r '.session_id')
flag_file="/tmp/claude_tools_${session_id}.txt"
echo "$tool_name" >> "$flag_file"
exit 0
```

**Stop hook:**
```bash
#!/bin/bash
input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id')
flag_file="/tmp/claude_tools_${session_id}.txt"

if [ -f "$flag_file" ]; then
  tools=$(cat "$flag_file")
  # ツール一覧を処理
  rm "$flag_file"
fi
exit 0
```

## 根拠

公式ドキュメント（https://code.claude.com/docs/en/hooks.md）より：

> Stop and SubagentStop Input
> `stop_hook_active` is true when Claude Code is already continuing as a result of a stop hook. Check this value **or process the transcript** to prevent Claude Code from running indefinitely.

この記述から、Stopイベントでtranscriptの処理が標準的な方法であることが示唆されている。

## 比較

| アプローチ | 用途 | 複雑性 |
|---------|------|--------|
| transcript解析 | 完全な履歴が必要な場合 | 中程度 |
| PostToolUse + Stop flag | 簡易的な追跡 | 低 |

## 注意点

- `transcript_path`は相対パスで提供される場合がある
- SessionEndやクリア時にフラグファイルをクリーンアップする
- hook実行タイムアウト（デフォルト60秒）を考慮する
