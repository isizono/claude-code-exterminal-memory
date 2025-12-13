"""タスク管理の基底クラス定義"""
from abc import ABC, abstractmethod


class TaskStatusManager(ABC):
    """タスクのステータス変更を管理する基底クラス"""

    @abstractmethod
    def on_status_change(
        self, task_id: int, old_status: str, new_status: str
    ) -> None:
        """
        ステータス変更時のフック

        Args:
            task_id: タスクID
            old_status: 変更前のステータス
            new_status: 変更後のステータス
        """
        pass

    @abstractmethod
    def on_blocked(self, task_id: int) -> int:
        """
        blocked状態になった時、自動でトピックを作成して返す

        Args:
            task_id: タスクID

        Returns:
            作成されたトピックのID
        """
        pass
