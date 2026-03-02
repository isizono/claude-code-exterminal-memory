"""hooks/pretooluse_hook.py のE2Eテスト

subprocess.runでpretooluse_hook.pyを呼び出し、stdin→stdoutの入出力をテスト。
テスト用にtmpディレクトリのstateを使う（HOOK_STATE_DIR環境変数）。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hooks.hook_state import HookState

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SESSION_ID = "e2e-test-session-001"


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """テスト用のstateディレクトリを返し、HookStateのBASE_DIRもオーバーライド"""
    monkeypatch.setattr(HookState, "BASE_DIR", tmp_path)
    return tmp_path


def _run_hook(input_data: dict, state_dir: Path) -> subprocess.CompletedProcess:
    """pretooluse_hook.pyをサブプロセスで実行する"""
    return subprocess.run(
        [sys.executable, "hooks/pretooluse_hook.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
        env={**os.environ, "HOOK_STATE_DIR": str(state_dir)},
    )


class TestNoFlags:
    """フラグなし → 空JSON"""

    def test_empty_json_when_no_flags(self, state_dir):
        result = _run_hook({"session_id": _SESSION_ID}, state_dir)
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}


class TestTopicNameNudge:
    """topic名nudgeフラグあり → system-reminder注入 + フラグ消去確認"""

    def test_topic_name_nudge_injection(self, state_dir):
        # フラグをセット
        state = HookState(_SESSION_ID)
        state.set_nudge_topic_name(42, "Correct Topic Name")

        result = _run_hook({"session_id": _SESSION_ID}, state_dir)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "<system-reminder>" in ctx
        assert "Topic #42" in ctx
        assert "Correct Topic Name" in ctx

    def test_topic_name_flag_cleared_after_nudge(self, state_dir):
        state = HookState(_SESSION_ID)
        state.set_nudge_topic_name(42, "Correct Topic Name")

        _run_hook({"session_id": _SESSION_ID}, state_dir)

        # フラグが消去されていることを確認
        assert state.pop_nudge_topic_name() is None

    def test_topic_name_sanitized(self, state_dir):
        """<>" がサニタイズされること"""
        state = HookState(_SESSION_ID)
        state.set_nudge_topic_name(99, '<script>"alert</script>')

        result = _run_hook({"session_id": _SESSION_ID}, state_dir)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]

        # <>" が除去されている
        assert "<script>" not in ctx
        assert '"alert' not in ctx
        assert "scriptalert/script" in ctx


class TestNudgePending:
    """nudge_pendingフラグあり → system-reminder注入 + フラグ消去確認"""

    def test_record_nudge_injection(self, state_dir):
        state = HookState(_SESSION_ID)
        state.set_nudge_pending()

        result = _run_hook({"session_id": _SESSION_ID}, state_dir)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "<system-reminder>" in ctx
        assert "Self-check before continuing" in ctx
        assert "add_decision" in ctx

    def test_pending_flag_cleared_after_nudge(self, state_dir):
        state = HookState(_SESSION_ID)
        state.set_nudge_pending()

        _run_hook({"session_id": _SESSION_ID}, state_dir)

        # フラグが消去されていることを確認
        assert state.pop_nudge_pending() is False


class TestBothFlags:
    """両方あり → topic名nudge優先"""

    def test_topic_name_takes_priority(self, state_dir):
        state = HookState(_SESSION_ID)
        state.set_nudge_topic_name(10, "Priority Topic")
        state.set_nudge_pending()

        result = _run_hook({"session_id": _SESSION_ID}, state_dir)
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]

        # topic名nudgeが出力される
        assert "Topic #10" in ctx
        assert "Priority Topic" in ctx

        # topic名フラグは消去されている
        assert state.pop_nudge_topic_name() is None

        # pending フラグは残っている（次ターンで処理される）
        assert state.pop_nudge_pending() is True


class TestEmptySessionId:
    """session_id空 → 空JSON"""

    def test_empty_session_id(self, state_dir):
        result = _run_hook({"session_id": ""}, state_dir)
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_null_session_id(self, state_dir):
        result = _run_hook({"session_id": None}, state_dir)
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}


class TestFailOpen:
    """例外→空JSON（フェイルオープン）"""

    def test_invalid_json_input(self, state_dir):
        """不正なJSON入力でもクラッシュせず空JSONを返す"""
        proc = subprocess.run(
            [sys.executable, "hooks/pretooluse_hook.py"],
            input="not valid json",
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
            env={**os.environ, "HOOK_STATE_DIR": str(state_dir)},
        )
        assert proc.returncode == 0
        assert json.loads(proc.stdout) == {}
        # stderrにエラーログが出ている
        assert "error" in proc.stderr.lower()
