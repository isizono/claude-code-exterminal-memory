#!/bin/bash
#
# PostToolUseフック: add_decision後にタスク追加をリマインドする
#
# 発火条件:
# - settings.jsonのmatcherにより、add_decision呼び出し時のみ実行される
#

set -e

echo '{"decision": "approve", "message": "決定事項を記録しました。関連するタスクの追加はありますか？（add_taskで追加できます）"}'
