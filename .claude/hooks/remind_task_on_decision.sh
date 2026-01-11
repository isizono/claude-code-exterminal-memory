#!/bin/bash
#
# PostToolUseフック: add_decision後にタスク追加をリマインドする
#
# 発火条件:
# - tool_name が "mcp__claude-code-exterminal-memory__add_decision" の場合
#

set -e

# stdinからJSON入力を読み込み
INPUT=$(cat)

# ツール名を取得
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# add_decisionの場合のみリマインドメッセージを出力
if [ "$TOOL_NAME" = "mcp__claude-code-exterminal-memory__add_decision" ]; then
  echo '{"decision": "approve", "message": "決定事項を記録しました。関連するタスクの追加はありますか？（add_taskで追加できます）"}'
else
  echo '{"decision": "approve"}'
fi
