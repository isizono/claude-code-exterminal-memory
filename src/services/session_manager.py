"""セッション管理モジュール

HTTPサーバーモードで使用するセッションカウント管理と自動停止ウォッチドッグを提供する。
セッション数が0になると猶予期間後にサーバーをシャットダウンする。
"""
import asyncio
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_GRACE_PERIOD_SEC = 30


class SessionManager:
    """セッションカウント管理 + 自動停止ウォッチドッグ

    スレッドセーフ。register/unregisterはHTTPリクエストハンドラから呼ばれる。
    ウォッチドッグはバックグラウンドスレッドで動作し、セッション0 → 猶予期間 → shutdownを行う。
    """

    def __init__(self, grace_period_sec: int = DEFAULT_GRACE_PERIOD_SEC):
        self._active_sessions: set[str] = set()
        self._lock = threading.Lock()
        self._grace_period = grace_period_sec
        self._shutdown_callback: Optional[Callable[[], None]] = None
        self._shutdown_event = threading.Event()
        self._cancel_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    @property
    def active_count(self) -> int:
        """アクティブセッション数を返す。"""
        with self._lock:
            return len(self._active_sessions)

    @property
    def session_ids(self) -> set[str]:
        """アクティブセッションIDのコピーを返す。"""
        with self._lock:
            return set(self._active_sessions)

    def register(self, session_id: str) -> bool:
        """セッションを登録する。

        Args:
            session_id: セッション識別子

        Returns:
            新規登録の場合True、既に登録済みの場合False
        """
        with self._lock:
            if session_id in self._active_sessions:
                logger.info(f"Session already registered: {session_id}")
                return False
            self._active_sessions.add(session_id)
            count = len(self._active_sessions)
            # ロック内でキャンセル（_start_grace_timerとのレースコンディション防止）
            self._cancel_event.set()

        logger.info(f"Session registered: {session_id} (active: {count})")
        return True

    def unregister(self, session_id: str) -> bool:
        """セッションを解除する。

        セッション数が0になった場合、猶予期間タイマーを開始する。

        Args:
            session_id: セッション識別子

        Returns:
            解除に成功した場合True、未登録の場合False
        """
        with self._lock:
            if session_id not in self._active_sessions:
                logger.warning(f"Session not found: {session_id}")
                return False
            self._active_sessions.discard(session_id)
            count = len(self._active_sessions)

        logger.info(f"Session unregistered: {session_id} (active: {count})")

        if count == 0:
            self._start_grace_timer()
        return True

    def set_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """シャットダウン時に呼ばれるコールバックを設定する。"""
        self._shutdown_callback = callback

    def start_watchdog(self) -> None:
        """ウォッチドッグスレッドを起動する。

        サーバー起動直後（セッション0の状態）から猶予期間タイマーを開始する。
        """
        self._start_grace_timer()

    def _start_grace_timer(self) -> None:
        """猶予期間タイマーを（再）開始する。"""
        with self._lock:
            # 既存のタイマーをキャンセル
            self._cancel_event.set()
            # 新しいイベントに置き換え（ロック内でregisterのset()と競合しない）
            self._cancel_event = threading.Event()
            cancel_event = self._cancel_event

        self._watchdog_thread = threading.Thread(
            target=self._grace_timer_worker,
            args=(cancel_event,),
            daemon=True,
        )
        self._watchdog_thread.start()

    def _grace_timer_worker(self, cancel_event: threading.Event) -> None:
        """猶予期間タイマーのワーカー。

        猶予期間中にcancel_eventがsetされたらタイマーをキャンセルする。
        猶予期間が経過してもセッション0の場合、shutdownコールバックを呼ぶ。
        """
        # 猶予期間待機（cancel_eventがsetされたら早期リターン）
        cancelled = cancel_event.wait(timeout=self._grace_period)
        if cancelled:
            return

        # 猶予期間経過後、セッション数を確認
        with self._lock:
            count = len(self._active_sessions)

        if count == 0:
            logger.info(
                f"No active sessions after {self._grace_period}s grace period, "
                "initiating shutdown"
            )
            self._shutdown_event.set()
            if self._shutdown_callback:
                self._shutdown_callback()
        else:
            logger.info(
                f"Grace period expired but {count} sessions active, "
                "cancelling shutdown"
            )

    @property
    def is_shutdown_requested(self) -> bool:
        """シャットダウンがリクエストされたかどうかを返す。"""
        return self._shutdown_event.is_set()
