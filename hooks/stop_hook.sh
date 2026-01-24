#!/bin/bash
#
# Stopフック: 毎ターンの会話を自動でログに記録する
#
# 処理フロー:
# 1. メタタグチェック → なければblock
# 2. トピック変更チェック → 前topicにdecisionなければblock
# 3. approve + バックグラウンドでログ記録
#
# 無限ループ防止:
#   record_log.py内でHaikuを呼ぶ際に --setting-sources "" を使用することで
#   プロジェクト設定（フック含む）を無視し、Stopフックが再発火しないようにしている

set -e

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 状態・ログディレクトリの設定
STATE_DIR="${HOME}/.claude/.claude-code-memory/state"
LOG_DIR="${HOME}/.claude/.claude-code-memory/logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

# stdinからJSON入力を読み込み
INPUT=$(cat)
echo "$INPUT" >> "$LOG_DIR/stop_hook_input.log"
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

# 1. メタタグチェック
META_RESULT=$(cd "$PROJECT_ROOT" && uv run python "$SCRIPT_DIR/parse_meta_tag.py" "$TRANSCRIPT_PATH" 2>&1)
META_EXIT_CODE=$?

if [ $META_EXIT_CODE -ne 0 ]; then
  # スクリプト実行エラー
  jq -n --arg reason "parse_meta_tag.py failed: $META_RESULT" '{decision: "block", reason: $reason}'
  exit 0
fi

META_FOUND=$(echo "$META_RESULT" | jq -r '.found')

if [ "$META_FOUND" != "true" ]; then
  echo '{"decision": "block", "reason": "応答の最後にメタタグを出力してください。フォーマット: <!-- [meta] project: xxx (id: N) | topic: yyy (id: M) -->"}'
  exit 0
fi

CURRENT_TOPIC=$(echo "$META_RESULT" | jq -r '.topic_id')

# 2. トピック変更チェック
PREV_TOPIC_FILE="${STATE_DIR}/prev_topic_${SESSION_ID}"
PREV_TOPIC=$(cat "$PREV_TOPIC_FILE" 2>/dev/null || echo "")

if [ -n "$PREV_TOPIC" ] && [ "$PREV_TOPIC" != "$CURRENT_TOPIC" ]; then
  # セッション開始直後のfirst_topic(topic_id=1)からの移動はスキップ
  if [ "$PREV_TOPIC" = "1" ]; then
    : # 何もしない（決定事項チェックをスキップ）
  else
    # 前のトピックにdecisionがあるかチェック
    DECISION_RESULT=$(cd "$PROJECT_ROOT" && uv run python "$SCRIPT_DIR/check_decision.py" "$PREV_TOPIC" 2>&1)
    DECISION_EXIT_CODE=$?

    if [ $DECISION_EXIT_CODE -ne 0 ]; then
      # スクリプト実行エラー
      jq -n --arg reason "check_decision.py failed: $DECISION_RESULT" '{decision: "block", reason: $reason}'
      exit 0
    fi

    if [ "$DECISION_RESULT" = "false" ]; then
      jq -n --arg topic "$PREV_TOPIC" '{decision: "block", reason: ("トピックが変わりました。前のトピック(id=" + $topic + ")に決定事項を記録してから移動してください")}'
      exit 0
    fi
  fi
fi

# 3. 現在のトピックを保存
echo "$CURRENT_TOPIC" > "$PREV_TOPIC_FILE"

# 4. ターン数カウント & sync_memoryリマインダー
TURN_COUNT_FILE="${STATE_DIR}/turn_count_${SESSION_ID}"
TURN_COUNT=$(cat "$TURN_COUNT_FILE" 2>/dev/null || echo "0")
TURN_COUNT=$((TURN_COUNT + 1))
echo "$TURN_COUNT" > "$TURN_COUNT_FILE"

SYNC_REMINDER=""
if [ $((TURN_COUNT % 3)) -eq 0 ]; then
  SYNC_REMINDER="<!-- [sync_memory推奨] ${TURN_COUNT}ターン経過しました。/sync_memory でセッション内容を記録することを検討してください。 -->"
fi

# 5. approve + バックグラウンドでログ記録
# nohupで完全にデタッチして、親プロセスの終了を待たせない
nohup bash -c "cd '$PROJECT_ROOT' && uv run python '$SCRIPT_DIR/record_log.py' '$TRANSCRIPT_PATH' '$CURRENT_TOPIC'" >> "$LOG_DIR/record_log.log" 2>&1 &
disown

# 6. 結果を出力
if [ -n "$SYNC_REMINDER" ]; then
  jq -n --arg reminder "$SYNC_REMINDER" '{decision: "approve", reason: $reminder}'
else
  echo '{"decision": "approve"}'
fi
exit 0
