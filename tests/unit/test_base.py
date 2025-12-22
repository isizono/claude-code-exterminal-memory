"""TaskStatusListenerの抽象クラステスト"""
import pytest
from src.base import TaskStatusListener


class ConcreteTaskStatusListener(TaskStatusListener):
    """テスト用の具象クラス"""

    def __init__(self):
        self.status_changes = []

    def on_status_change(self, task_id: int, new_status: str) -> None:
        """ステータス変更を記録"""
        self.status_changes.append((task_id, new_status))


def test_cannot_instantiate_abstract_class():
    """抽象クラスを直接インスタンス化できないことを確認"""
    with pytest.raises(TypeError) as exc_info:
        TaskStatusListener()
    assert "Can't instantiate abstract class" in str(exc_info.value)


def test_concrete_class_can_be_instantiated():
    """抽象メソッドを全て実装したクラスはインスタンス化できる"""
    listener = ConcreteTaskStatusListener()
    assert isinstance(listener, TaskStatusListener)


def test_on_status_change_is_called():
    """on_status_changeメソッドが正しく呼び出される"""
    listener = ConcreteTaskStatusListener()
    listener.on_status_change(1, "in_progress")
    listener.on_status_change(1, "completed")

    assert len(listener.status_changes) == 2
    assert listener.status_changes[0] == (1, "in_progress")
    assert listener.status_changes[1] == (1, "completed")


def test_status_change_with_different_statuses():
    """様々なステータスで動作することを確認"""
    listener = ConcreteTaskStatusListener()
    statuses = ["pending", "in_progress", "blocked", "completed"]

    for i, status in enumerate(statuses, start=1):
        listener.on_status_change(i, status)

    assert len(listener.status_changes) == 4
    for i, status in enumerate(statuses, start=1):
        assert listener.status_changes[i - 1] == (i, status)
