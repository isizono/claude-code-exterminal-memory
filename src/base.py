"""タスクステータス変更のリスナー定義"""
from abc import ABC, abstractmethod


class TaskStatusListener(ABC):
    """タスクのステータス変更を監視する抽象クラス"""

    @abstractmethod
    def on_status_change(self, task_id: int, new_status: str) -> None:
        """
        ステータス変更時のフック

        Args:
            task_id: タスクID
            new_status: 変更後のステータス
        """
        pass
