"""リモートMCPサーバー（GitHub OAuth認証付き）

mount方式でmain.pyのmcpインスタンスを取り込み、
GitHub OAuth認証付きの別サーバーとして起動する。
internal版（main.py）への変更はゼロ。

環境変数:
    GITHUB_CLIENT_ID: GitHub OAuth AppのClient ID
    GITHUB_CLIENT_SECRET: GitHub OAuth AppのClient Secret
    CC_MEMORY_BASE_URL: 公開URL（例: https://cc-memory.example.com）
"""
import os
import logging

from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider

from src.db import verify_sqlite_vec, init_database
from src.main import mcp as internal_mcp

logger = logging.getLogger(__name__)

REMOTE_PORT = 8001


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise SystemExit(f"環境変数 {key} が未設定です")
    return value


def create_remote_server() -> FastMCP:
    """認証付きリモートサーバーを作成する"""
    auth = GitHubProvider(
        client_id=_require_env("GITHUB_CLIENT_ID"),
        client_secret=_require_env("GITHUB_CLIENT_SECRET"),
        base_url=_require_env("CC_MEMORY_BASE_URL"),
    )

    remote = FastMCP("cc-memory-remote", auth=auth)
    remote.mount(internal_mcp)
    return remote


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    verify_sqlite_vec()
    init_database()

    server = create_remote_server()
    logger.info(f"Starting remote server on port {REMOTE_PORT}")
    server.run(transport="streamable-http", host="127.0.0.1", port=REMOTE_PORT)
