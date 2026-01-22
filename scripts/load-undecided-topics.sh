#!/bin/bash
#
# SessionStart フック: セッション開始時の初期化処理
#
# 処理内容:
# 1. PREV_TOPIC_FILE を削除（Stopフックのトピック変更チェック用）
# 2. 未決定トピック確認のリマインドを出力
#
# このフックは以下のタイミングで発火する:
# - startup: 新規セッション開始時
# - resume: --resume, --continue, /resume で復帰時
# - clear: /clear コマンド実行時
# - compact: コンパクト実行時

# stdinからJSON入力を読み込み
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

# PREV_TOPIC_FILE を削除（存在しなくてもエラーにしない）
# これにより、/clear後や新規セッション開始時に
# 前のトピック情報が残って誤検知することを防ぐ
rm -f "/tmp/claude_prev_topic_${SESSION_ID}" 2>/dev/null || true

echo "セッション開始時: このプロジェクトの未決定トピックを get_undecided_topics で取得し、各トピックの決定事項（get_decisions）も把握しておいてください。必要に応じて議論ログ（get_logs）も取得可能です。"
