#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
指定topic_idがDBに存在するかチェックするスクリプト。
Stopフックからメタタグparse後に呼び出される。

Usage:
    python check_topic_exists.py <topic_id>

Returns:
    "true" if topic exists, "false" otherwise
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.db import execute_query


def main():
    # 引数がない場合は「存在しない」として正常終了
    if len(sys.argv) < 2:
        print("false")
        sys.exit(0)

    try:
        topic_id = int(sys.argv[1])
    except ValueError:
        # 不正な引数はエラー（exit 1）
        print(f"Error: Invalid topic_id: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)

    try:
        rows = execute_query(
            "SELECT id FROM discussion_topics WHERE id = ?",
            (topic_id,),
        )
        if len(rows) > 0:
            print("true")
        else:
            print("false")
    except Exception as e:
        # DBエラーはエラー（exit 1）
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
