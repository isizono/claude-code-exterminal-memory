#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0"]
# ///
"""
指定トピックに決定事項があるかチェックするスクリプト。
Stopフックからトピック変更時に呼び出される。

Usage:
    python check_decision.py <topic_id>

Returns:
    "true" if decisions exist, "false" otherwise
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.services.decision_service import get_decisions


def main():
    # 引数がない場合は「決定事項なし」として正常終了
    if len(sys.argv) < 2:
        print("false")
        sys.exit(0)

    try:
        topic_id = int(sys.argv[1])
    except ValueError:
        # 不正な引数はエラー（exit 1）
        print(f"Error: Invalid topic_id: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)

    result = get_decisions(topic_id, limit=1)

    if "error" in result:
        # DBエラーはエラー（exit 1）
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    decisions = result.get("decisions", [])
    if len(decisions) > 0:
        print("true")
    else:
        print("false")
    # 正常終了は常にexit 0


if __name__ == "__main__":
    main()
