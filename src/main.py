"""MCPサーバーのメインエントリーポイント"""
from fastmcp import FastMCP
from typing import Optional
from src.db import execute_insert, execute_query, row_to_dict, init_database

# MCPサーバーを作成
mcp = FastMCP("Discussion Recording System")


# 実装ロジック（テストから直接呼べるようにMCPデコレータと分離）
def add_project_impl(
    name: str,
    description: Optional[str] = None,
    asana_url: Optional[str] = None,
) -> dict:
    """
    新しいプロジェクトを追加する。

    Args:
        name: プロジェクト名（ユニーク）
        description: プロジェクトの説明
        asana_url: AsanaプロジェクトタスクのURL

    Returns:
        作成されたプロジェクト情報
    """
    try:
        project_id = execute_insert(
            "INSERT INTO projects (name, description, asana_url) VALUES (?, ?, ?)",
            (name, description, asana_url),
        )

        # 作成したプロジェクトを取得
        rows = execute_query(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        if rows:
            project = row_to_dict(rows[0])
            return {
                "project_id": project["id"],
                "name": project["name"],
                "description": project["description"],
                "asana_url": project["asana_url"],
                "created_at": project["created_at"],
            }
        else:
            raise Exception("Failed to retrieve created project")

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


def get_projects_impl(limit: int = 30) -> dict:
    """
    プロジェクト一覧を取得する。

    Args:
        limit: 取得件数上限（最大30件）

    Returns:
        プロジェクト一覧
    """
    try:
        # limitを30件に制限
        limit = min(limit, 30)

        rows = execute_query(
            "SELECT * FROM projects ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )

        projects = []
        for row in rows:
            project = row_to_dict(row)
            projects.append({
                "id": project["id"],
                "name": project["name"],
                "description": project["description"],
                "asana_url": project["asana_url"],
                "created_at": project["created_at"],
            })

        return {"projects": projects}

    except Exception as e:
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": str(e),
            }
        }


# MCPツール定義
@mcp.tool()
def add_project(
    name: str,
    description: Optional[str] = None,
    asana_url: Optional[str] = None,
) -> dict:
    """
    新しいプロジェクトを追加する。

    Args:
        name: プロジェクト名（ユニーク）
        description: プロジェクトの説明
        asana_url: AsanaプロジェクトタスクのURL

    Returns:
        作成されたプロジェクト情報
    """
    return add_project_impl(name, description, asana_url)


@mcp.tool()
def get_projects(limit: int = 30) -> dict:
    """
    プロジェクト一覧を取得する。

    Args:
        limit: 取得件数上限（最大30件）

    Returns:
        プロジェクト一覧
    """
    return get_projects_impl(limit)
