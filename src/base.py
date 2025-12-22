"""タスク管理の基底クラス定義"""
from abc import ABC, abstractmethod
from typing import Optional


class TaskStatusManager(ABC):
    """タスクのステータス変更を管理する基底クラス

    PR #18 (tasksテーブル実装) がマージされることを前提とした設計。
    タスクのステータス管理とblocked時の自動トピック作成を担当する。
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

    @abstractmethod
    def on_blocked(self, task_id: int) -> Optional[int]:
        """
        blocked状態になった時、自動でトピックを作成して返す

        Args:
            task_id: タスクID

        Returns:
            作成されたトピックのID（失敗時はNone）

        Raises:
            ValueError: task_idが無効な場合
            RuntimeError: トピック作成に失敗した場合
        """
        pass
