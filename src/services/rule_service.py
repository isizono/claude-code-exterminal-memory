"""ルール管理サービス"""
import logging

from src.db import get_connection, row_to_dict

logger = logging.getLogger(__name__)


def add_rule(content: str) -> dict:
    """ルールを追加する。

    Args:
        content: ルールの内容（空文字不可）

    Returns:
        作成されたルール情報
    """
    if not content or not content.strip():
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "content must not be empty",
            }
        }

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO rules (content) VALUES (?)",
            (content,),
        )
        rule_id = cursor.lastrowid
        conn.commit()

        row = conn.execute(
            "SELECT * FROM rules WHERE id = ?",
            (rule_id,),
        ).fetchone()
        if not row:
            raise Exception("Failed to retrieve created rule")

        rule = row_to_dict(row)
        return {
            "rule_id": rule["id"],
            "content": rule["content"],
            "active": rule["active"],
            "created_at": rule["created_at"],
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


def list_rules() -> dict:
    """ルール一覧を取得する。

    Returns:
        ルール一覧とtotal_count
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM rules ORDER BY id"
        ).fetchall()

        rules = []
        for row in rows:
            rule = row_to_dict(row)
            rules.append({
                "rule_id": rule["id"],
                "content": rule["content"],
                "active": rule["active"],
                "created_at": rule["created_at"],
            })

        return {
            "rules": rules,
            "total_count": len(rules),
        }

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }
    finally:
        conn.close()


def update_rule(rule_id: int, content: str | None = None, active: int | None = None) -> dict:
    """ルールを更新する。

    Args:
        rule_id: ルールID
        content: 新しい内容（optional）
        active: 有効/無効フラグ（0 or 1、optional）

    Returns:
        更新されたルール情報
    """
    if content is None and active is None:
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "At least one of content or active must be provided",
            }
        }

    if content is not None and not content.strip():
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "content must not be empty",
            }
        }

    if active is not None and active not in (0, 1):
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "active must be 0 or 1",
            }
        }

    conn = get_connection()
    try:
        # 存在チェック
        row = conn.execute(
            "SELECT * FROM rules WHERE id = ?",
            (rule_id,),
        ).fetchone()
        if not row:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Rule with id {rule_id} not found",
                }
            }

        # 動的SQL構築
        set_parts = []
        values = []

        if content is not None:
            set_parts.append("content = ?")
            values.append(content)

        if active is not None:
            set_parts.append("active = ?")
            values.append(active)

        set_clause = ", ".join(set_parts)
        values.append(rule_id)

        conn.execute(
            f"UPDATE rules SET {set_clause} WHERE id = ?",
            tuple(values),
        )
        conn.commit()

        # 更新後のルールを取得
        row = conn.execute(
            "SELECT * FROM rules WHERE id = ?",
            (rule_id,),
        ).fetchone()
        if not row:
            raise Exception("Failed to retrieve updated rule")

        rule = row_to_dict(row)
        return {
            "rule_id": rule["id"],
            "content": rule["content"],
            "active": rule["active"],
            "created_at": rule["created_at"],
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
