#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
SessionStartフック: セッション開始時のコンテキスト自動注入

処理内容:
1. prev_topicファイルを削除（Stopフックのトピック変更チェック用リセット）
2. 直近7日以内にトピック更新があったアクティブプロジェクトを取得
3. 各プロジェクトの最新トピック3件 + in_progressタスクをJSON出力
"""
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.db import execute_query

STATE_DIR = Path.home() / ".claude" / ".claude-code-memory" / "state"
DESC_MAX_LEN = 30


def cleanup_prev_topic(session_id: str) -> None:
    """prev_topicファイルを削除する"""
    prev_topic_file = STATE_DIR / f"prev_topic_{session_id}"
    prev_topic_file.unlink(missing_ok=True)


def get_active_projects() -> list[dict]:
    """直近7日以内にトピック更新があったプロジェクトを取得する"""
    rows = execute_query(
        """
        SELECT DISTINCT p.id, p.name
        FROM projects p
        JOIN discussion_topics t ON p.id = t.project_id
        WHERE t.created_at > datetime('now', '-7 days')
        ORDER BY p.id
        """
    )
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def get_recent_topics(project_id: int) -> list[dict]:
    """プロジェクトの最新トピック3件を取得する"""
    rows = execute_query(
        """
        SELECT id, title, description
        FROM discussion_topics
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 3
        """,
        (project_id,),
    )
    results = []
    for row in rows:
        desc = row["description"] or ""
        if len(desc) > DESC_MAX_LEN:
            desc = desc[:DESC_MAX_LEN] + "..."
        results.append({"id": row["id"], "title": row["title"], "description": desc})
    return results


def get_in_progress_tasks(project_id: int) -> list[dict]:
    """プロジェクトのin_progressタスクを取得する"""
    rows = execute_query(
        """
        SELECT id, title
        FROM tasks
        WHERE project_id = ? AND status = 'in_progress'
        ORDER BY updated_at DESC
        """,
        (project_id,),
    )
    return [{"id": row["id"], "title": row["title"]} for row in rows]


def main():
    # stdinからJSON入力を読み込み
    input_data = json.loads(sys.stdin.read())
    session_id = input_data.get("session_id", "")

    # 1. prev_topicファイルを削除
    cleanup_prev_topic(session_id)

    # 2. アクティブプロジェクトを取得し、コンテキストを構築
    projects = get_active_projects()
    for project in projects:
        project["recent_topics"] = get_recent_topics(project["id"])
        project["in_progress_tasks"] = get_in_progress_tasks(project["id"])

    # 3. JSON出力
    output = {"active_projects": projects}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"load_active_context: DB not found - {e}", file=sys.stderr)
    except Exception as e:
        print(f"load_active_context: {type(e).__name__}: {e}", file=sys.stderr)
