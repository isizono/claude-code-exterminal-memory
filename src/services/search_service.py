"""FTS5統合検索サービス"""
import sqlite3
from typing import Optional
from src.db import execute_query, row_to_dict


VALID_TYPES = {'topic', 'decision', 'task'}

TYPE_TO_TABLE = {
    'topic': 'discussion_topics',
    'decision': 'decisions',
    'task': 'tasks',
}


def _escape_fts5_query(keyword: str) -> str:
    """FTS5クエリ用のエスケープ処理。ダブルクォートで囲む。"""
    # ダブルクォート内のダブルクォートは2つ重ねてエスケープ
    escaped = keyword.replace('"', '""')
    return f'"{escaped}"'


def search(
    project_id: int,
    keyword: str,
    type_filter: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    プロジェクト内をキーワードで横断検索する。

    FTS5 trigramトークナイザによる部分文字列マッチ。3文字以上のキーワードを指定する。
    結果はBM25スコア順でランキングされる。
    詳細情報が必要な場合は get_by_id(type, id) で取得する。

    Args:
        project_id: プロジェクトID
        keyword: 検索キーワード（3文字以上）
        type_filter: 検索対象の絞り込み（'topic', 'decision', 'task'。未指定で全種類）
        limit: 取得件数上限（デフォルト10件、最大50件）

    Returns:
        検索結果一覧（type, id, title, score）
    """
    # バリデーション
    keyword = keyword.strip()
    if len(keyword) < 3:
        return {
            "error": {
                "code": "KEYWORD_TOO_SHORT",
                "message": "keyword must be at least 3 characters for trigram search"
            }
        }

    if type_filter is not None and type_filter not in VALID_TYPES:
        return {
            "error": {
                "code": "INVALID_TYPE_FILTER",
                "message": f"Invalid type_filter: {type_filter}. Must be one of {sorted(VALID_TYPES)}"
            }
        }

    limit = max(1, min(limit, 50))

    try:
        escaped_keyword = _escape_fts5_query(keyword)

        rows = execute_query(
            """
            SELECT
              si.source_type AS type,
              si.source_id AS id,
              si.title,
              bm25(search_index_fts, 5.0, 1.0) AS score
            FROM search_index_fts
            JOIN search_index si ON si.id = search_index_fts.rowid
            WHERE search_index_fts MATCH ?
              AND si.project_id = ?
              AND (? IS NULL OR si.source_type = ?)
            ORDER BY score
            LIMIT ?
            """,
            (escaped_keyword, project_id, type_filter, type_filter, limit),
        )

        results = []
        for row in rows:
            r = row_to_dict(row)
            results.append({
                "type": r["type"],
                "id": r["id"],
                "title": r["title"],
                "score": r["score"],
            })

        return {"results": results, "total_count": len(results)}

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


def _format_row(type_name: str, data: dict) -> dict:
    """typeに応じたレスポンス整形"""
    if type_name == 'topic':
        return {
            "id": data["id"],
            "project_id": data["project_id"],
            "title": data["title"],
            "description": data["description"],
            "parent_topic_id": data["parent_topic_id"],
            "created_at": data["created_at"],
        }
    elif type_name == 'decision':
        return {
            "id": data["id"],
            "topic_id": data["topic_id"],
            "decision": data["decision"],
            "reason": data["reason"],
            "created_at": data["created_at"],
        }
    elif type_name == 'task':
        return {
            "id": data["id"],
            "project_id": data["project_id"],
            "title": data["title"],
            "description": data["description"],
            "status": data["status"],
            "topic_id": data["topic_id"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        }
    return data


def get_by_id(type: str, id: int) -> dict:
    """
    search結果の詳細情報を取得する。

    searchツールで得られたtype + idの組み合わせを指定して、
    元データの完全な情報を取得する。

    Args:
        type: データ種別（'topic', 'decision', 'task'）
        id: データのID

    Returns:
        指定した種別に応じた詳細情報
    """
    if type not in VALID_TYPES:
        return {
            "error": {
                "code": "INVALID_TYPE",
                "message": f"Invalid type: {type}. Must be one of {sorted(VALID_TYPES)}"
            }
        }

    table = TYPE_TO_TABLE[type]

    try:
        rows = execute_query(f"SELECT * FROM {table} WHERE id = ?", (id,))
        if not rows:
            return {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"{type} with id {id} not found"
                }
            }

        return {"type": type, "data": _format_row(type, row_to_dict(rows[0]))}

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
