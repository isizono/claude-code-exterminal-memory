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
  NUDGE_MSG="<system-reminder>Self-check before continuing: (1) Does your current topic still match the conversation? If the discussion has shifted, create a new topic with add_topic. (2) Have you and the user reached any agreements that should be recorded? Examples: design choices, naming conventions, scope boundaries, implementation approaches, or trade-off resolutions. If yes, record them now with add_decision before proceeding.</system-reminder>"

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
