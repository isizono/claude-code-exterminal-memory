"""データベース操作の基底クラス"""
import re
import sqlite3
from abc import ABC
from typing import Any, Optional

from src.db import execute_query, get_connection, row_to_dict

# カラム名として許可されるパターン（英小文字で始まり、英数字とアンダースコアのみ）
_VALID_COLUMN_NAME = re.compile(r'^[a-z][a-z0-9_]*$')


def _validate_column_names(columns: list[str]) -> None:
    """カラム名がSQLインジェクションに安全かバリデーション"""
    for col in columns:
        if not _VALID_COLUMN_NAME.match(col):
            raise ValueError(f"Invalid column name: {col}")


class BaseDBService(ABC):
    """データベース操作の基底クラス

    updated_atの自動更新など、共通のDB操作を提供する
    """

    table_name: str = ""  # 継承先でテーブル名を指定

    def __init_subclass__(cls, **kwargs):
        """サブクラス作成時にtable_nameのバリデーションを実行"""
        super().__init_subclass__(**kwargs)
        if not cls.table_name:
            raise ValueError(f"{cls.__name__} must define table_name")
        if not cls.table_name.replace('_', '').isalnum():
            raise ValueError(f"Invalid table_name: {cls.table_name}")

    def _execute_insert(self, fields: dict[str, Any]) -> int:
        """
        INSERT操作を実行
        created_atはテーブルのデフォルト値により自動設定される

        Args:
            fields: 挿入するフィールドの辞書

        Returns:
            挿入されたレコードのID

        Raises:
            ValueError: カラム名が不正な場合
        """
        column_names = list(fields.keys())
        _validate_column_names(column_names)

        columns = ', '.join(column_names)
        placeholders = ', '.join(['?' for _ in fields])
        values = tuple(fields.values())

        conn = get_connection()
        try:
            cursor = conn.execute(
                f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
                values
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"INSERT実行エラー: {e}") from e
        finally:
            conn.close()

    def _execute_update(self, id: int, fields: dict[str, Any]) -> None:
        """
        UPDATE操作を実行（updated_atを自動更新）

        Args:
            id: 更新対象のレコードID
            fields: 更新するフィールドの辞書

        Raises:
            ValueError: カラム名が不正な場合
        """
        column_names = list(fields.keys())
        _validate_column_names(column_names)

        set_parts = []
        values = []

        for k, v in fields.items():
            set_parts.append(f"{k} = ?")
            values.append(v)

        # updated_atは常に追加
        set_parts.append("updated_at = CURRENT_TIMESTAMP")

        set_clause = ', '.join(set_parts)
        conn = get_connection()
        try:
            conn.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                tuple(values) + (id,)
            )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"UPDATE実行エラー: {e}") from e
        finally:
            conn.close()

    def _get_by_id(self, id: int) -> Optional[dict[str, Any]]:
        """
        IDでレコードを取得

        Args:
            id: レコードID

        Returns:
            レコード（存在しない場合はNone）
        """
        rows = execute_query(
            f"SELECT * FROM {self.table_name} WHERE id = ?",
            (id,)
        )
        return row_to_dict(rows[0]) if rows else None

    def _delete(self, id: int) -> None:
        """
        レコードを削除

        Args:
            id: 削除対象のレコードID
        """
        conn = get_connection()
        try:
            conn.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (id,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"DELETE実行エラー: {e}") from e
        finally:
            conn.close()
