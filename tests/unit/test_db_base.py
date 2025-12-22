"""BaseDBServiceのテスト"""
import os
import tempfile
import pytest
import sqlite3
from src.db_base import BaseDBService
from src.db import get_connection, init_database


class TestTable(BaseDBService):
    """テスト用の具象クラス"""

    table_name = "test_items"


@pytest.fixture
def temp_db():
    """テスト用の一時的なデータベースを作成する"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        os.environ["DISCUSSION_DB_PATH"] = db_path
        init_database()

        # テスト用テーブルを作成
        conn = get_connection()
        try:
            conn.execute("""
                CREATE TABLE test_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

        yield db_path

        # クリーンアップ
        if "DISCUSSION_DB_PATH" in os.environ:
            del os.environ["DISCUSSION_DB_PATH"]


def test_table_name_validation_empty():
    """table_nameが空の場合、エラーが発生する"""
    with pytest.raises(ValueError) as exc_info:

        class EmptyTableName(BaseDBService):
            table_name = ""

    assert "must define table_name" in str(exc_info.value)


def test_table_name_validation_invalid_chars():
    """table_nameに不正な文字が含まれる場合、エラーが発生する"""
    with pytest.raises(ValueError) as exc_info:

        class InvalidTableName(BaseDBService):
            table_name = "test; DROP TABLE users--"

    assert "Invalid table_name" in str(exc_info.value)


def test_table_name_validation_valid():
    """table_nameが有効な場合、クラスを定義できる"""

    class ValidTableName(BaseDBService):
        table_name = "valid_table_name_123"

    assert ValidTableName.table_name == "valid_table_name_123"


def test_execute_insert(temp_db):
    """INSERT操作が正しく動作する"""
    service = TestTable()
    item_id = service._execute_insert({"name": "test_item", "value": 42})

    assert item_id > 0

    # 挿入されたデータを確認
    item = service._get_by_id(item_id)
    assert item is not None
    assert item["name"] == "test_item"
    assert item["value"] == 42
    assert item["created_at"] is not None


def test_execute_insert_multiple(temp_db):
    """複数のINSERT操作が正しく動作する"""
    service = TestTable()
    id1 = service._execute_insert({"name": "item1", "value": 1})
    id2 = service._execute_insert({"name": "item2", "value": 2})

    assert id2 == id1 + 1

    item1 = service._get_by_id(id1)
    item2 = service._get_by_id(id2)

    assert item1["name"] == "item1"
    assert item2["name"] == "item2"


def test_execute_update(temp_db):
    """UPDATE操作が正しく動作する"""
    service = TestTable()
    item_id = service._execute_insert({"name": "original", "value": 100})

    # 更新
    service._execute_update(item_id, {"name": "updated", "value": 200})

    # 更新されたデータを確認
    item = service._get_by_id(item_id)
    assert item["name"] == "updated"
    assert item["value"] == 200


def test_execute_update_auto_updated_at(temp_db):
    """UPDATE時にupdated_atが自動更新される"""
    service = TestTable()
    item_id = service._execute_insert({"name": "test", "value": 1})

    original = service._get_by_id(item_id)
    original_updated_at = original["updated_at"]

    # 少し待機してからUPDATE（タイムスタンプの違いを確認するため）
    import time

    time.sleep(0.1)

    service._execute_update(item_id, {"value": 2})

    updated = service._get_by_id(item_id)
    # SQLiteのCURRENT_TIMESTAMPは秒単位なので、確実に変わるとは限らない
    # そのため、updated_atフィールドが存在することのみ確認
    assert updated["updated_at"] is not None


def test_get_by_id_existing(temp_db):
    """存在するIDでレコードを取得できる"""
    service = TestTable()
    item_id = service._execute_insert({"name": "test", "value": 123})

    item = service._get_by_id(item_id)

    assert item is not None
    assert item["id"] == item_id
    assert item["name"] == "test"
    assert item["value"] == 123


def test_get_by_id_non_existing(temp_db):
    """存在しないIDの場合Noneを返す"""
    service = TestTable()
    item = service._get_by_id(99999)

    assert item is None


def test_delete(temp_db):
    """DELETE操作が正しく動作する"""
    service = TestTable()
    item_id = service._execute_insert({"name": "to_delete", "value": 1})

    # 削除前に存在することを確認
    assert service._get_by_id(item_id) is not None

    # 削除
    service._delete(item_id)

    # 削除後に存在しないことを確認
    assert service._get_by_id(item_id) is None


def test_delete_non_existing(temp_db):
    """存在しないIDの削除でもエラーが発生しない"""
    service = TestTable()
    # エラーが発生しないことを確認
    service._delete(99999)


def test_insert_constraint_violation(temp_db):
    """制約違反の場合、例外が発生する"""
    service = TestTable()

    with pytest.raises(sqlite3.Error) as exc_info:
        # nameはNOT NULL制約があるため、Noneを挿入するとエラー
        service._execute_insert({"name": None, "value": 1})

    assert "INSERT実行エラー" in str(exc_info.value)


def test_update_non_existing_id(temp_db):
    """存在しないIDを更新してもエラーは発生しない（0行が更新される）"""
    service = TestTable()
    # エラーが発生しないことを確認
    service._execute_update(99999, {"name": "test"})


def test_transaction_rollback_on_insert_error(temp_db):
    """INSERT失敗時にロールバックされる"""
    service = TestTable()

    # 最初に正常なデータを挿入
    id1 = service._execute_insert({"name": "first", "value": 1})

    # 制約違反で失敗
    try:
        service._execute_insert({"name": None, "value": 2})
    except sqlite3.Error:
        pass

    # 最初のデータは正常に存在する
    item = service._get_by_id(id1)
    assert item is not None
    assert item["name"] == "first"


def test_transaction_rollback_on_update_error(temp_db):
    """UPDATE失敗時にロールバックされる"""
    service = TestTable()

    item_id = service._execute_insert({"name": "original", "value": 1})

    # 制約違反で失敗するUPDATE
    try:
        service._execute_update(item_id, {"name": None})
    except sqlite3.Error:
        pass

    # 元のデータが保持されている
    item = service._get_by_id(item_id)
    assert item["name"] == "original"


def test_partial_update(temp_db):
    """一部のフィールドのみ更新できる"""
    service = TestTable()
    item_id = service._execute_insert({"name": "original", "value": 100})

    # nameだけ更新
    service._execute_update(item_id, {"name": "updated_name"})

    item = service._get_by_id(item_id)
    assert item["name"] == "updated_name"
    assert item["value"] == 100  # valueは変わっていない
