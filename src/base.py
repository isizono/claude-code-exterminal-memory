"""タスク管理の基底クラス定義"""
from abc import ABC, abstractmethod


class TaskStatusManager(ABC):
    """タスクのステータス変更を管理する基底クラス

    PR #18 (tasksテーブル実装) がマージされることを前提とした設計。
    """

    @abstractmethod
    def on_status_change(self, task_id: int, new_status: str) -> None:
        """
        ステータス変更時のフック

        Args:
            task_id: タスクID
            new_status: 変更後のステータス

        Note:
            変更前のステータスはtask_idから取得可能なため、引数から削除しました。
        """
        pass
