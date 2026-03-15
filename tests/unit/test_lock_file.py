"""lock_fileモジュールのユニットテスト"""
import json
import os

import pytest

from src.services import lock_file


@pytest.fixture(autouse=True)
def isolate_lock_file(tmp_path, monkeypatch):
    """テストごとにロックファイルのパスを一時ディレクトリに差し替える"""
    lock_dir = tmp_path / ".cc-memory"
    lock_dir.mkdir()
    monkeypatch.setattr(lock_file, "LOCK_DIR", lock_dir)
    monkeypatch.setattr(lock_file, "LOCK_FILE", lock_dir / "server.lock")


class TestAcquire:
    def test_acquire_creates_lock_file(self):
        """ロックファイルが作成される"""
        assert lock_file.acquire(52837) is True
        info = lock_file.read()
        assert info is not None
        assert info["pid"] == os.getpid()
        assert info["port"] == 52837

    def test_acquire_fails_when_process_alive(self):
        """自プロセスでロック取得後、再取得は失敗する"""
        assert lock_file.acquire(52837) is True
        assert lock_file.acquire(52837) is False

    def test_acquire_reclaims_stale_lock(self, monkeypatch):
        """死んだプロセスのロックファイルは上書きされる"""
        # 存在しないPIDでロックファイルを手動作成
        stale_pid = 99999999
        monkeypatch.setattr(lock_file, "_is_process_alive", lambda pid: False)
        lock_file.LOCK_FILE.write_text(
            json.dumps({"pid": stale_pid, "port": 52837}), encoding="utf-8"
        )

        assert lock_file.acquire(52837) is True
        info = lock_file.read()
        assert info["pid"] == os.getpid()

    def test_acquire_creates_directory(self, tmp_path, monkeypatch):
        """LOCK_DIRが存在しない場合も自動作成される"""
        new_dir = tmp_path / "nonexistent" / ".cc-memory"
        monkeypatch.setattr(lock_file, "LOCK_DIR", new_dir)
        monkeypatch.setattr(lock_file, "LOCK_FILE", new_dir / "server.lock")

        assert lock_file.acquire(52837) is True
        assert new_dir.exists()


class TestRead:
    def test_read_returns_none_when_no_file(self):
        """ファイルがない場合はNoneを返す"""
        assert lock_file.read() is None

    def test_read_returns_none_on_malformed_json(self):
        """JSONが壊れている場合はNoneを返す"""
        lock_file.LOCK_FILE.write_text("not json", encoding="utf-8")
        assert lock_file.read() is None

    def test_read_returns_none_on_missing_fields(self):
        """必須フィールドがない場合はNoneを返す"""
        lock_file.LOCK_FILE.write_text(json.dumps({"pid": 1}), encoding="utf-8")
        assert lock_file.read() is None

    def test_read_returns_info(self):
        """正常なロックファイルの読み取り"""
        lock_file.acquire(52837)
        info = lock_file.read()
        assert info is not None
        assert info["pid"] == os.getpid()
        assert info["port"] == 52837


class TestRelease:
    def test_release_removes_lock_file(self):
        """自プロセスのロックファイルを削除する"""
        lock_file.acquire(52837)
        lock_file.release()
        assert lock_file.read() is None

    def test_release_noop_when_no_file(self):
        """ファイルがない場合は何もしない"""
        lock_file.release()  # 例外が出なければOK

    def test_release_skips_other_process_lock(self):
        """他プロセスのロックファイルは削除しない"""
        lock_file.LOCK_FILE.write_text(
            json.dumps({"pid": 99999999, "port": 52837}), encoding="utf-8"
        )
        lock_file.release()
        assert lock_file.read() is not None  # 削除されていない


class TestIsProcessAlive:
    def test_current_process_is_alive(self):
        """自プロセスは生存している"""
        assert lock_file._is_process_alive(os.getpid()) is True

    def test_nonexistent_process(self):
        """存在しないPIDはFalse"""
        assert lock_file._is_process_alive(99999999) is False
