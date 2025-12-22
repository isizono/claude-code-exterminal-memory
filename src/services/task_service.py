"""タスク管理サービス"""
import logging
import sqlite3
from typing import Optional

from src.db import execute_query, row_to_dict
from src.db_base import BaseDBService
from src.base import TaskStatusListener
from src.services.topic_service import add_topic

logger = logging.getLogger(__name__)

# 有効なステータス値
VALID_STATUSES = {"pending", "in_progress", "completed", "blocked"}


class TaskStatusManagerImpl(TaskStatusListener):
    """タスクのステータス変更を管理する実装クラス"""

    def on_status_change(self, task_id: int, new_status: str) -> None:
        """
        ステータス変更時のフック

        Args:
            task_id: タスクID
            new_status: 変更後のステータス
        """
        logger.info(f"Task {task_id}: status changed to '{new_status}'")

    def on_blocked(self, task_id: int) -> int:
        """
        blocked状態になった時、自動でトピックを作成して返す

        Args:
            task_id: タスクID

        Returns:
            作成されたトピックのID
        """
        # タスク情報を取得
        rows = execute_query(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        )

        if not rows:
            raise ValueError(f"Task with id {task_id} not found")

        task = row_to_dict(rows[0])

        # トピックを作成
        topic_title = f"[BLOCKED] {task['title']}"
        topic_description = f"""
タスクがブロックされました。

## タスク情報
- タイトル: {task['title']}
- 説明: {task['description']}

## ブロック理由
このタスクは進行中にブロック状態になりました。
議論を通じてブロック解消の方法を検討してください。
"""

        result = add_topic(
            project_id=task["project_id"],
            title=topic_title,
            description=topic_description.strip(),
            parent_topic_id=None,
        )

        if "error" in result:
            raise Exception(
                f"Failed to create topic: {result['error']['message']}"
            )

        return result["topic_id"]


class TaskDBService(BaseDBService):
    """タスクのDB操作を管理するサービス"""

    table_name = "tasks"


# グローバルインスタンス
_task_db = TaskDBService()


def _task_to_response(task: dict) -> dict:
    """タスクデータをAPIレスポンス形式に変換"""
    return {
        "task_id": task["id"],
        "project_id": task["project_id"],
        "title": task["title"],
        "description": task["description"],
        "status": task["status"],
        "topic_id": task["topic_id"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
    }


def add_task(project_id: int, title: str, description: str) -> dict:
    """
    タスクを作成してIDを返す

    Args:
        project_id: プロジェクトID
        title: タスクのタイトル
        description: タスクの説明

    Returns:
        作成されたタスク情報
    """
    try:
        task_id = _task_db._execute_insert({
            'project_id': project_id,
            'title': title,
            'description': description,
            'status': 'pending'
        })

        # 作成したタスクを取得
        task = _task_db._get_by_id(task_id)
        if not task:
            raise Exception("Failed to retrieve created task")
        return _task_to_response(task)

    except sqlite3.IntegrityError as e:
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_tasks(project_id: int, status: Optional[str] = None) -> dict:
    """
    タスク一覧を取得（statusでフィルタ可能）

    Args:
        project_id: プロジェクトID
        status: フィルタするステータス（未指定なら全件取得）

    Returns:
        タスク一覧
    """
    try:
        if status is None:
            rows = execute_query(
                """
                SELECT * FROM tasks
                WHERE project_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (project_id,),
            )
        else:
            rows = execute_query(
                """
                SELECT * FROM tasks
                WHERE project_id = ? AND status = ?
                ORDER BY created_at ASC, id ASC
                """,
                (project_id, status),
            )

        tasks = []
        for row in rows:
            task = row_to_dict(row)
            tasks.append({
                "id": task["id"],
                "project_id": task["project_id"],
                "title": task["title"],
                "description": task["description"],
                "status": task["status"],
                "topic_id": task["topic_id"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
            })

        return {"tasks": tasks}

    except sqlite3.IntegrityError as e:
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def update_task_status(task_id: int, new_status: str) -> dict:
    """
    ステータスを更新
    blockedになった場合は自動でトピックを作成してtopic_idを設定

    Args:
        task_id: タスクID
        new_status: 新しいステータス

    Returns:
        更新されたタスク情報
    """
    # ステータスバリデーション
    if new_status not in VALID_STATUSES:
        return {
            "error": {
                "code": "INVALID_STATUS",
                "message": f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}",
            }
        }

    try:
        # 現在のタスク情報を取得
        task = _task_db._get_by_id(task_id)
        if not task:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Task with id {task_id} not found",
                }
            }

        # ステータスマネージャーのインスタンスを作成
        manager = TaskStatusManagerImpl()

        # ステータス変更フックを呼び出し
        manager.on_status_change(task_id, new_status)

        # blockedになった場合はトピックを作成
        update_fields = {'status': new_status}
        if new_status == "blocked":
            topic_id = manager.on_blocked(task_id)
            update_fields['topic_id'] = topic_id

        # ステータスを更新（updated_atは自動で追加される）
        _task_db._execute_update(task_id, update_fields)

        # 更新後のタスクを取得
        task = _task_db._get_by_id(task_id)
        if not task:
            raise Exception("Failed to retrieve updated task")
        return _task_to_response(task)

    except sqlite3.IntegrityError as e:
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }
