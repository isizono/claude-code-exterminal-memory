"""サブジェクト管理サービス"""
import sqlite3
from typing import Optional
from src.db import execute_insert, execute_query, get_connection, row_to_dict


def add_subject(
    name: str,
    description: str,
) -> dict:
    """
    新しいサブジェクトを追加する。

    Args:
        name: サブジェクト名（ユニーク）
        description: サブジェクトの説明（必須）

    Returns:
        作成されたサブジェクト情報
    """
    try:
        subject_id = execute_insert(
            "INSERT INTO subjects (name, description) VALUES (?, ?)",
            (name, description),
        )

        # 作成したサブジェクトを取得
        rows = execute_query(
            "SELECT * FROM subjects WHERE id = ?", (subject_id,)
        )
        if rows:
            subject = row_to_dict(rows[0])
            return {
                "subject_id": subject["id"],
                "name": subject["name"],
                "description": subject["description"],
                "created_at": subject["created_at"],
            }
        else:
            raise Exception("Failed to retrieve created subject")

    except sqlite3.IntegrityError as e:
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def list_subjects() -> dict:
    """
    サブジェクト一覧を取得する（id + name のみの軽量版）。

    Returns:
        サブジェクト一覧（id, name）
    """
    try:
        rows = execute_query(
            "SELECT id, name FROM subjects ORDER BY created_at DESC, id DESC",
        )

        subjects = []
        for row in rows:
            subjects.append({
                "id": row["id"],
                "name": row["name"],
            })

        return {"subjects": subjects}

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def update_subject(
    subject_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """
    サブジェクトを更新する（名前、説明を変更可能）

    Args:
        subject_id: サブジェクトID
        name: 新しいサブジェクト名（optional）
        description: 新しい説明（optional）

    Returns:
        更新されたサブジェクト情報
    """
    # 最低1つのオプショナルパラメータが必要
    if name is None and description is None:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "At least one of name or description must be provided",
            }
        }

    # 空文字バリデーション
    if name is not None and name.strip() == "":
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "name must not be empty",
            }
        }

    if description is not None and description.strip() == "":
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "description must not be empty",
            }
        }

    conn = get_connection()
    try:
        # 現在のサブジェクト情報を取得
        cursor = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        row = cursor.fetchone()
        if not row:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Subject with id {subject_id} not found",
                }
            }

        # 動的SQL構築: 指定されたフィールドのみUPDATEする
        set_parts = []
        values = []

        if name is not None:
            set_parts.append("name = ?")
            values.append(name)

        if description is not None:
            set_parts.append("description = ?")
            values.append(description)

        set_clause = ", ".join(set_parts)
        values.append(subject_id)

        conn.execute(
            f"UPDATE subjects SET {set_clause} WHERE id = ?",
            tuple(values),
        )

        conn.commit()

        # 更新後のサブジェクトを取得
        cursor = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        row = cursor.fetchone()
        if not row:
            raise Exception("Failed to retrieve updated subject")
        subject = row_to_dict(row)
        return {
            "subject_id": subject["id"],
            "name": subject["name"],
            "description": subject["description"],
            "created_at": subject["created_at"],
        }

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return {
            "error": {
                "code": "CONSTRAINT_VIOLATION",
                "message": str(e),
            }
        }
    except Exception as e:
        conn.rollback()
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }
    finally:
        conn.close()
