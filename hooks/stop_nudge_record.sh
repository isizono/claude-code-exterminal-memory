#!/bin/bash
#
# Stop hook: nudgeカウンター管理
#
# 処理フロー:
# 1. カウンターをインクリメント
# 2. 3の倍数のとき、transcriptから直近3ターン分のadd_decision/add_topic呼び出しをチェック
# 3. 呼び出しがなければnudge_pendingフラグを書く
# 4. 常にapprove
#
# 注意: stop_enforce_metatag.sh の後に実行されること（metatag blockでカウントされないように）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

STATE_DIR="${HOME}/.claude/.claude-code-memory/state"
LOG_DIR="${HOME}/.claude/.claude-code-memory/logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

# stdinからJSON入力を読み込み
INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

# SESSION_IDが空またはnullの場合はスキップ
if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
  echo '{"decision": "approve"}'
  exit 0
fi

# SESSION_IDのスラッシュをアンダースコアに置換（パス安全化）
SESSION_ID_SAFE="${SESSION_ID//\//_}"
COUNTER_FILE="${STATE_DIR}/nudge_counter_${SESSION_ID_SAFE}"
PENDING_FILE="${STATE_DIR}/nudge_pending_${SESSION_ID_SAFE}"

# 1. カウンターをインクリメント
COUNTER=$(cat "$COUNTER_FILE" 2>/dev/null || echo "0")
COUNTER=$((COUNTER + 1))
echo "$COUNTER" > "$COUNTER_FILE"

# 2. 3の倍数のときチェック
if [ $((COUNTER % 3)) -eq 0 ]; then
  RECORDED=$(python3 "$SCRIPT_DIR/check_recent_recording.py" "$TRANSCRIPT_PATH" 3 2>>"$LOG_DIR/nudge_stderr.log")

  # 3. 結果に応じて処理
  if [ "$RECORDED" = "true" ]; then
    # 直近3ターンに記録があったらカウンターをリセット（次のチェックまで3ターン猶予）
    echo "0" > "$COUNTER_FILE"
  else
    # 呼び出しがなければnudge_pendingフラグを書く
    echo "1" > "$PENDING_FILE"
  fi
fi

# 4. 常にapprove
echo '{"decision": "approve"}'
exit 0
