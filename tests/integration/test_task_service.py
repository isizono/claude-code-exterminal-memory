"""タスクサービスの統合テスト"""
import os
import tempfile
import pytest
from src.db import init_database, execute_query
from src.services.project_service import add_project
from src.services.task_service import add_task, get_tasks, update_task_status


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
def project_with_task(temp_db):
    """プロジェクトとタスクを作成するフィクスチャ"""
    project = add_project(name="test-project", description="Test Project")
    task = add_task(
        project_id=project["project_id"],
        title="Test Task",
        description="This is a test task"
    )
    return {"project": project, "task": task}


class TestAddTask:
    """add_taskの統合テスト"""

    def test_add_task_success(self, temp_db):
        """タスクの追加が成功する"""
        project = add_project(name="test-project", description="Test")
        result = add_task(
            project_id=project["project_id"],
            title="New Task",
            description="Task description"
        )

        assert "error" not in result
        assert result["task_id"] > 0
        assert result["title"] == "New Task"
        assert result["description"] == "Task description"
        assert result["status"] == "pending"
        assert result["topic_id"] is None

    def test_add_task_invalid_project(self, temp_db):
        """存在しないプロジェクトIDでエラーになる"""
        result = add_task(
            project_id=9999,
            title="Task",
            description="Description"
        )

        assert "error" in result
        # FK制約違反はDATABASE_ERRORとして返される
        assert result["error"]["code"] == "DATABASE_ERROR"


class TestGetTasks:
    """get_tasksの統合テスト"""

    def test_get_tasks_empty(self, temp_db):
        """タスクが存在しない場合、空のリストが返る"""
        project = add_project(name="test-project", description="Test")
        result = get_tasks(project_id=project["project_id"])

        assert "error" not in result
        assert result["tasks"] == []

    def test_get_tasks_with_status_filter(self, temp_db):
        """ステータスでフィルタできる"""
        project = add_project(name="test-project", description="Test")
        pid = project["project_id"]

        add_task(project_id=pid, title="Task 1", description="Desc 1")
        task2 = add_task(project_id=pid, title="Task 2", description="Desc 2")
        add_task(project_id=pid, title="Task 3", description="Desc 3")

        # Task 2をin_progressに変更
        update_task_status(task2["task_id"], "in_progress")

        # in_progressでフィルタ
        result = get_tasks(project_id=pid, status="in_progress")

        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["title"] == "Task 2"


class TestUpdateTaskStatus:
    """update_task_statusの統合テスト"""

    def test_update_status_to_in_progress(self, project_with_task):
        """ステータスをin_progressに更新できる"""
        task = project_with_task["task"]
        result = update_task_status(task["task_id"], "in_progress")

        assert "error" not in result
        assert result["status"] == "in_progress"
        assert result["topic_id"] is None  # blockedじゃないのでtopic_idはNoneのまま

    def test_update_status_to_completed(self, project_with_task):
        """ステータスをcompletedに更新できる"""
        task = project_with_task["task"]
        result = update_task_status(task["task_id"], "completed")

        assert "error" not in result
        assert result["status"] == "completed"

    def test_update_status_invalid(self, project_with_task):
        """無効なステータスでエラーになる"""
        task = project_with_task["task"]
        result = update_task_status(task["task_id"], "invalid_status")

        assert "error" in result
        assert result["error"]["code"] == "INVALID_STATUS"

    def test_update_status_task_not_found(self, temp_db):
        """存在しないタスクIDでエラーになる"""
        result = update_task_status(9999, "in_progress")

        assert "error" in result
        assert result["error"]["code"] == "NOT_FOUND"


class TestBlockedStatusWithTopicCreation:
    """blockedステータス変更時のトピック自動作成の統合テスト"""

    def test_blocked_creates_topic(self, project_with_task):
        """blockedに変更するとトピックが自動作成される"""
        task = project_with_task["task"]
        result = update_task_status(task["task_id"], "blocked")

        assert "error" not in result
        assert result["status"] == "blocked"
        assert result["topic_id"] is not None

    def test_blocked_topic_has_correct_title(self, project_with_task):
        """作成されたトピックのタイトルが正しい形式になる"""
        task = project_with_task["task"]
        result = update_task_status(task["task_id"], "blocked")

        # DBから直接トピックを確認
        rows = execute_query(
            "SELECT * FROM discussion_topics WHERE id = ?",
            (result["topic_id"],)
        )
        assert len(rows) == 1

        topic = dict(rows[0])
        assert topic["title"] == f"[BLOCKED] {task['title']}"
        assert topic["description"] == task["description"]

    def test_blocked_topic_linked_to_correct_project(self, project_with_task):
        """作成されたトピックが正しいプロジェクトに紐づく"""
        project = project_with_task["project"]
        task = project_with_task["task"]
        result = update_task_status(task["task_id"], "blocked")

        rows = execute_query(
            "SELECT * FROM discussion_topics WHERE id = ?",
            (result["topic_id"],)
        )
        topic = dict(rows[0])
        assert topic["project_id"] == project["project_id"]

    def test_blocked_then_unblocked_keeps_topic_id(self, project_with_task):
        """blockedからin_progressに戻してもtopic_idは維持される"""
        task = project_with_task["task"]

        # blocked に変更
        blocked_result = update_task_status(task["task_id"], "blocked")
        topic_id = blocked_result["topic_id"]

        # in_progress に戻す
        unblocked_result = update_task_status(task["task_id"], "in_progress")

        # topic_id は維持される（消えない）
        assert unblocked_result["topic_id"] == topic_id

    def test_multiple_tasks_blocked_create_separate_topics(self, temp_db):
        """複数のタスクをblockedにするとそれぞれ別のトピックが作成される"""
        project = add_project(name="test-project", description="Test")
        pid = project["project_id"]

        task1 = add_task(project_id=pid, title="Task 1", description="Desc 1")
        task2 = add_task(project_id=pid, title="Task 2", description="Desc 2")

        result1 = update_task_status(task1["task_id"], "blocked")
        result2 = update_task_status(task2["task_id"], "blocked")

        assert result1["topic_id"] != result2["topic_id"]

        # トピックが2つ作成されている
        rows = execute_query("SELECT COUNT(*) as count FROM discussion_topics", ())
        assert rows[0]["count"] == 2
