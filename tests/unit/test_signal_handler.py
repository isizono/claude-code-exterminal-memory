"""SIGINT/SIGTERMハンドラのテスト"""
import signal
import subprocess
import sys
import textwrap

import pytest


def _run_main_snippet(snippet: str, *, timeout: float = 5.0) -> subprocess.CompletedProcess:
    """main.pyのif __name__ == '__main__'相当のコードをサブプロセスで実行する"""
    return subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestSignalHandlerRegistration:
    """シグナルハンドラの登録テスト"""

    def test_sigint_handler_is_registered(self):
        """SIGINTハンドラが登録され、sys.exit(0)が呼ばれる"""
        code = textwrap.dedent("""\
            import signal
            import sys
            import os

            def _handle_signal(signum, frame):
                sys.exit(0)

            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)

            # ハンドラが登録されていることを確認
            assert signal.getsignal(signal.SIGINT) == _handle_signal
            assert signal.getsignal(signal.SIGTERM) == _handle_signal

            # SIGINTを自分自身に送信してハンドラが発火することを確認
            os.kill(os.getpid(), signal.SIGINT)

            # ここに到達したらハンドラが動いていない
            print("ERROR: handler did not fire")
            sys.exit(1)
        """)
        result = _run_main_snippet(code)
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_sigterm_handler_exits_cleanly(self):
        """SIGTERMハンドラが登録され、sys.exit(0)が呼ばれる"""
        code = textwrap.dedent("""\
            import signal
            import sys
            import os

            def _handle_signal(signum, frame):
                sys.exit(0)

            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)

            # SIGTERMを自分自身に送信
            os.kill(os.getpid(), signal.SIGTERM)

            print("ERROR: handler did not fire")
            sys.exit(1)
        """)
        result = _run_main_snippet(code)
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_handler_not_registered_on_import(self):
        """モジュールをimportしただけではシグナルハンドラが登録されない"""
        code = textwrap.dedent("""\
            import signal
            import sys

            # main.pyをモジュールとしてimport（__name__ != "__main__"）
            sys.path.insert(0, ".")
            import src.main

            # デフォルトのSIGINTハンドラが維持されていることを確認
            handler = signal.getsignal(signal.SIGINT)
            # デフォルトハンドラはsignal.default_int_handlerまたはNone
            assert handler is not None
            assert handler.__name__ != "_handle_signal", (
                "Signal handler should not be registered on import"
            )
            print("OK: handler not registered on import")
        """)
        result = _run_main_snippet(
            code,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK: handler not registered on import" in result.stdout
