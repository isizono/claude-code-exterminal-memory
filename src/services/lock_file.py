"""ロックファイル管理モジュール

HTTPサーバーモードで使用するロックファイルの作成・読み取り・削除を行う。
ロックファイルにはPID・ポート情報を記録し、サーバーの多重起動を防止する。
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

LOCK_DIR = Path.home() / ".cc-memory"
LOCK_FILE = LOCK_DIR / "server.lock"


class LockInfo(TypedDict):
    """ロックファイルに記録する情報"""
    pid: int
    port: int


def acquire(port: int) -> bool:
    """ロックファイルを作成する。

    既に有効なロックファイルが存在する場合（プロセスが生存中）はFalseを返す。
    プロセスが死んでいる場合はロックファイルを上書きする（stale lock回収）。

    Args:
        port: サーバーのポート番号

    Returns:
        ロック取得に成功した場合True
    """
    LOCK_DIR.mkdir(parents=True, exist_ok=True)

    existing = read()
    if existing is not None:
        # プロセスが生存しているか確認
        if _is_process_alive(existing["pid"]):
            logger.warning(
                f"Server already running: pid={existing['pid']}, port={existing['port']}"
            )
            return False
        # stale lock — 上書き
        logger.info(f"Removing stale lock file: pid={existing['pid']}")

    info: LockInfo = {"pid": os.getpid(), "port": port}
    try:
        LOCK_FILE.write_text(json.dumps(info), encoding="utf-8")
        logger.info(f"Lock file created: {LOCK_FILE}")
        return True
    except OSError as e:
        logger.error(f"Failed to create lock file: {e}")
        return False


def read() -> Optional[LockInfo]:
    """ロックファイルを読み取る。

    Returns:
        ロック情報。ファイルが存在しない or パースエラーの場合はNone
    """
    if not LOCK_FILE.exists():
        return None
    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "pid" in data and "port" in data:
            return LockInfo(pid=data["pid"], port=data["port"])
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read lock file: {e}")
        return None


def release() -> None:
    """ロックファイルを削除する。

    自プロセスのPIDと一致する場合のみ削除する。
    ファイルが存在しない場合は何もしない。
    """
    existing = read()
    if existing is None:
        return
    if existing["pid"] != os.getpid():
        logger.warning(
            f"Lock file owned by another process: pid={existing['pid']}, skipping release"
        )
        return
    try:
        LOCK_FILE.unlink()
        logger.info("Lock file released")
    except OSError as e:
        logger.warning(f"Failed to release lock file: {e}")


def _is_process_alive(pid: int) -> bool:
    """指定PIDのプロセスが生存しているか確認する。"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # プロセスは存在するが権限がない → 生存している
        return True
