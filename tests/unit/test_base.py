"""TaskStatusManagerの抽象クラステスト"""
import pytest
from typing import Optional
from src.base import TaskStatusManager


class ConcreteTaskStatusManager(TaskStatusManager):
    """テスト用の具象クラス"""

    def __init__(self):
        self.status_changes = []
        self.blocked_calls = []

    def on_status_change(self, task_id: int, new_status: str) -> None:
        """ステータス変更を記録"""
        self.status_changes.append((task_id, new_status))

    def on_blocked(self, task_id: int) -> Optional[int]:
        """blocked時の処理を記録して、ダミーのトピックIDを返す"""
        self.blocked_calls.append(task_id)
        return 999  # ダミーのトピックID


class IncompleteTaskStatusManager(TaskStatusManager):
    """抽象メソッドを実装していない不完全なクラス"""

    def on_status_change(self, task_id: int, new_status: str) -> None:
        pass
    # on_blockedを実装していない


def test_cannot_instantiate_abstract_class():
    """抽象クラスを直接インスタンス化できないことを確認"""
    with pytest.raises(TypeError) as exc_info:
        TaskStatusManager()
    assert "Can't instantiate abstract class" in str(exc_info.value)


def test_concrete_class_can_be_instantiated():
    """抽象メソッドを全て実装したクラスはインスタンス化できる"""
    manager = ConcreteTaskStatusManager()
    assert isinstance(manager, TaskStatusManager)


def test_incomplete_class_cannot_be_instantiated():
    """抽象メソッドを一部実装していないクラスはインスタンス化できない"""
    with pytest.raises(TypeError) as exc_info:
        IncompleteTaskStatusManager()
    assert "Can't instantiate abstract class" in str(exc_info.value)
    assert "on_blocked" in str(exc_info.value)


def test_on_status_change_is_called():
    """on_status_changeメソッドが正しく呼び出される"""
    manager = ConcreteTaskStatusManager()
    manager.on_status_change(1, "in_progress")
    manager.on_status_change(1, "completed")

    assert len(manager.status_changes) == 2
    assert manager.status_changes[0] == (1, "in_progress")
    assert manager.status_changes[1] == (1, "completed")


def test_on_blocked_returns_topic_id():
    """on_blockedメソッドがトピックIDを返す"""
    manager = ConcreteTaskStatusManager()
    topic_id = manager.on_blocked(1)

    assert topic_id == 999
    assert 1 in manager.blocked_calls


def test_on_blocked_can_return_none():
    """on_blockedメソッドがNoneを返すことができる"""

    class NoneReturningManager(TaskStatusManager):
        def on_status_change(self, task_id: int, new_status: str) -> None:
            pass

        def on_blocked(self, task_id: int) -> Optional[int]:
            return None

    manager = NoneReturningManager()
    result = manager.on_blocked(1)
    assert result is None


def test_status_change_with_different_statuses():
    """様々なステータスで動作することを確認"""
    manager = ConcreteTaskStatusManager()
    statuses = ["pending", "in_progress", "blocked", "completed"]

    for i, status in enumerate(statuses, start=1):
        manager.on_status_change(i, status)

    assert len(manager.status_changes) == 4
    for i, status in enumerate(statuses, start=1):
        assert manager.status_changes[i - 1] == (i, status)


def test_multiple_tasks_blocked():
    """複数のタスクがブロックされた場合の動作"""
    manager = ConcreteTaskStatusManager()

    topic_ids = [manager.on_blocked(i) for i in range(1, 4)]

    assert len(manager.blocked_calls) == 3
    assert manager.blocked_calls == [1, 2, 3]
    assert all(tid == 999 for tid in topic_ids)
