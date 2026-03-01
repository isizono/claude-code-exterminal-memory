"""タスクサービスの統合テスト"""
import os
import tempfile
import pytest
from src.db import init_database, execute_query
from src.services.subject_service import add_subject
from src.services.task_service import add_task, get_tasks, update_task


@pytest.fixture
def temp_db():
    """テスト用の一時的なデータベースを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        os.environ["DISCUSSION_DB_PATH"] = db_path
        init_database()
        yield db_path
        if "DISCUSSION_DB_PATH" in os.environ:
            del os.environ["DISCUSSION_DB_PATH"]


@pytest.fixture
def subject_with_task(temp_db):
    """サブジェクトとタスクを作成するフィクスチャ"""
    subject = add_subject(name="test-subject", description="Test Subject")
    task = add_task(
        subject_id=subject["subject_id"],
        title="Test Task",
        description="This is a test task"
    )
    return {"subject": subject, "task": task}


class TestAddTask:
    """add_taskの統合テスト"""

    def test_add_task_success(self, temp_db):
        """タスクの追加が成功する"""
        subject = add_subject(name="test-subject", description="Test")
        result = add_task(
            subject_id=subject["subject_id"],
            title="New Task",
            description="Task description"
        )

        assert "error" not in result
        assert result["task_id"] > 0
        assert result["title"] == "New Task"
        assert result["description"] == "Task description"
        assert result["status"] == "pending"
        assert result["topic_id"] is None

    def test_add_task_invalid_subject(self, temp_db):
        """存在しないサブジェクトIDでエラーになる"""
        result = add_task(
            subject_id=9999,
            title="Task",
            description="Description"
        )

        assert "error" in result
        # FK制約違反はCONSTRAINT_VIOLATIONとして返される
        assert result["error"]["code"] == "CONSTRAINT_VIOLATION"


class TestGetTasks:
    """get_tasksの統合テスト"""

    def test_get_tasks_empty(self, temp_db):
        """タスクが存在しない場合、空のリストが返る"""
        subject = add_subject(name="test-subject", description="Test")
        result = get_tasks(subject_id=subject["subject_id"], status="pending")

        assert "error" not in result
        assert result["tasks"] == []
        assert result["total_count"] == 0

    def test_get_tasks_with_status_filter(self, temp_db):
        """ステータスでフィルタできる"""
        subject = add_subject(name="test-subject", description="Test")
        sid = subject["subject_id"]

        add_task(subject_id=sid, title="Task 1", description="Desc 1")
        task2 = add_task(subject_id=sid, title="Task 2", description="Desc 2")
        add_task(subject_id=sid, title="Task 3", description="Desc 3")

        # Task 2をin_progressに変更
        update_task(task2["task_id"], new_status="in_progress")

        # in_progressでフィルタ
        result = get_tasks(subject_id=sid, status="in_progress")

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Task 2"
        assert result["total_count"] == 1

    def test_get_tasks_default_status_is_in_progress(self, temp_db):
        """statusなしで呼んだらin_progressのみ返る"""
        subject = add_subject(name="test-subject", description="Test")
        sid = subject["subject_id"]

        # pending x2, in_progress x1 を作成
        add_task(subject_id=sid, title="Pending 1", description="Desc")
        task_ip = add_task(subject_id=sid, title="In Progress 1", description="Desc")
        add_task(subject_id=sid, title="Pending 2", description="Desc")

        update_task(task_ip["task_id"], new_status="in_progress")

        # statusを指定せずに呼び出し → デフォルトでin_progressのみ
        result = get_tasks(subject_id=sid)

        assert "error" not in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "In Progress 1"
        assert result["total_count"] == 1

    def test_get_tasks_limit(self, temp_db):
        """limitが正しく動作する（タスク10件作成、limit=3で3件のみ返る）"""
        subject = add_subject(name="test-subject", description="Test")
        sid = subject["subject_id"]

        # pending状態のタスクを10件作成
        for i in range(10):
            add_task(subject_id=sid, title=f"Task {i}", description=f"Desc {i}")

        result = get_tasks(subject_id=sid, status="pending", limit=3)

        assert "error" not in result
        assert len(result["tasks"]) == 3

    def test_get_tasks_total_count(self, temp_db):
        """total_countが正しい全件数を返す"""
        subject = add_subject(name="test-subject", description="Test")
        sid = subject["subject_id"]

        # pending状態のタスクを5件作成
        for i in range(5):
            add_task(subject_id=sid, title=f"Task {i}", description=f"Desc {i}")

        result = get_tasks(subject_id=sid, status="pending")

        assert "error" not in result
        assert result["total_count"] == 5
        assert len(result["tasks"]) == 5

    def test_get_tasks_total_count_exceeds_limit(self, temp_db):
        """limit超過時にtotal_countは全件数、tasksはlimit分のみ"""
        subject = add_subject(name="test-subject", description="Test")
        sid = subject["subject_id"]

        # pending状態のタスクを8件作成
        for i in range(8):
            add_task(subject_id=sid, title=f"Task {i}", description=f"Desc {i}")

        result = get_tasks(subject_id=sid, status="pending", limit=3)

        assert "error" not in result
        assert result["total_count"] == 8  # 全件数
        assert len(result["tasks"]) == 3   # limit分のみ


    def test_get_tasks_invalid_limit_zero(self, temp_db):
        """limit=0でINVALID_PARAMETERエラーになる"""
        subject = add_subject(name="test-subject", description="Test")
        result = get_tasks(subject_id=subject["subject_id"], status="pending", limit=0)

        assert "error" in result
        assert result["error"]["code"] == "INVALID_PARAMETER"

    def test_get_tasks_invalid_limit_negative(self, temp_db):
        """limit=-1でINVALID_PARAMETERエラーになる"""
        subject = add_subject(name="test-subject", description="Test")
        result = get_tasks(subject_id=subject["subject_id"], status="pending", limit=-1)

        assert "error" in result
        assert result["error"]["code"] == "INVALID_PARAMETER"

    def test_get_tasks_invalid_status(self, temp_db):
        """無効なstatusでINVALID_STATUSエラーになる"""
        subject = add_subject(name="test-subject", description="Test")
        result = get_tasks(subject_id=subject["subject_id"], status="invalid_status")

        assert "error" in result
        assert result["error"]["code"] == "INVALID_STATUS"


class TestUpdateTask:
    """update_taskの統合テスト"""

    def test_update_status_to_in_progress(self, subject_with_task):
        """ステータスをin_progressに更新できる"""
        task = subject_with_task["task"]
        result = update_task(task["task_id"], new_status="in_progress")

        assert "error" not in result
        assert result["status"] == "in_progress"

    def test_update_status_to_completed(self, subject_with_task):
        """ステータスをcompletedに更新できる"""
        task = subject_with_task["task"]
        result = update_task(task["task_id"], new_status="completed")

        assert "error" not in result
        assert result["status"] == "completed"

    def test_update_status_invalid(self, subject_with_task):
        """無効なステータスでエラーになる"""
        task = subject_with_task["task"]
        result = update_task(task["task_id"], new_status="invalid_status")

        assert "error" in result
        assert result["error"]["code"] == "INVALID_STATUS"

    def test_update_task_not_found(self, temp_db):
        """存在しないタスクIDでエラーになる"""
        result = update_task(9999, new_status="in_progress")

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"
