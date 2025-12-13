"""データベース操作の基底クラス"""
from abc import ABC
from typing import Optional
from src.db import get_connection, execute_query, row_to_dict
import sqlite3


class BaseDBService(ABC):
    """データベース操作の基底クラス

    updated_atの自動更新など、共通のDB操作を提供する
    """

    table_name: str = ""  # 継承先でテーブル名を指定

    def _execute_insert(self, fields: dict) -> int:
        """
        INSERT操作を実行
        created_atは自動で追加される（デフォルト値）

        Args:
            fields: 挿入するフィールドの辞書

        Returns:
            挿入されたレコードのID
        """
        columns = ', '.join(fields.keys())
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

    def _execute_update(self, id: int, fields: dict) -> None:
        """
        UPDATE操作を実行（updated_atを自動追加）

        Args:
            id: 更新対象のレコードID
            fields: 更新するフィールドの辞書
        """
        # updated_atを自動追加
        fields['updated_at'] = 'CURRENT_TIMESTAMP'

        set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
        # CURRENT_TIMESTAMPは文字列として渡すとSQLiteが解釈してくれる
        values = []
        for v in fields.values():
            if v == 'CURRENT_TIMESTAMP':
                values.append(v)
            else:
                values.append(v)
        values = tuple(values) + (id,)

        # CURRENT_TIMESTAMPをプレースホルダーではなく直接埋め込む
        set_parts = []
        value_list = []
        for k, v in fields.items():
            if v == 'CURRENT_TIMESTAMP':
                set_parts.append(f"{k} = CURRENT_TIMESTAMP")
            else:
                set_parts.append(f"{k} = ?")
                value_list.append(v)

        set_clause = ', '.join(set_parts)
        values = tuple(value_list) + (id,)

        conn = get_connection()
        try:
            conn.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise sqlite3.Error(f"UPDATE実行エラー: {e}") from e
        finally:
            conn.close()

    def _get_by_id(self, id: int) -> Optional[dict]:
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
