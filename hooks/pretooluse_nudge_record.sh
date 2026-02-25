#!/bin/bash
#
# PreToolUse hook: nudgeリマインダー注入
#
# 処理フロー:
# 1. nudge_pendingフラグがあればadditionalContextにリマインダーを注入してフラグ消去
# 2. なければ何もしない（空JSON出力）

STATE_DIR="${HOME}/.claude/.claude-code-memory/state"
mkdir -p "$STATE_DIR"

# stdinからJSON入力を読み込み
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

# SESSION_IDが空またはnullの場合はスキップ
if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
  echo '{}'
  exit 0
fi

# SESSION_IDのスラッシュをアンダースコアに置換（パス安全化）
SESSION_ID_SAFE="${SESSION_ID//\//_}"
PENDING_FILE="${STATE_DIR}/nudge_pending_${SESSION_ID_SAFE}"

if [ -f "$PENDING_FILE" ]; then
  # フラグを消去
  rm -f "$PENDING_FILE"

  # additionalContextにリマインダーを注入
  NUDGE_MSG="<system-reminder>The decision/topic recording tools (add_decision, add_topic) haven't been used recently. If there are any agreements, design choices, or noteworthy conclusions from the recent conversation, consider recording them with add_decision. Ignore if not applicable.</system-reminder>"

  jq -n --arg ctx "$NUDGE_MSG" '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "additionalContext": $ctx
    }
  }'
else
  # 何もしない
  echo '{}'
fi

exit 0
