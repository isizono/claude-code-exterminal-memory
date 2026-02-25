"""サブジェクト管理サービス"""
import sqlite3
from src.db import execute_insert, execute_query, row_to_dict


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
