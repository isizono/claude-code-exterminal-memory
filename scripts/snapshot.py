"""DB自動スナップショット: 取得・ヘルスチェック・ローテーション・復元

SessionStart hookから呼び出される。独立モジュールとして動作し、
db_pathベースでスナップショットの管理を行う。
"""
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# プロジェクトルートをパスに追加（src.config等の参照用）
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

HEALTH_CHECK_TABLES = [
    "discussion_topics",
    "decisions",
    "discussion_logs",
    "activities",
    "materials",
]

SNAPSHOT_PREFIX = "discussion_"
SNAPSHOT_DB_SUFFIX = ".db"
SNAPSHOT_JSON_SUFFIX = ".json"


@dataclass
class HealthCheckResult:
    """ヘルスチェック結果"""
    is_healthy: bool = True
    warnings: list[str] = field(default_factory=list)
    current_counts: dict[str, int] = field(default_factory=dict)
    previous_counts: dict[str, int] = field(default_factory=dict)


def _get_snapshot_dir(db_path: str) -> Path:
    """スナップショット保存ディレクトリを返す（DBと同階層の snapshots/）"""
    return Path(db_path).parent / "snapshots"


def get_row_counts(db_path: str) -> dict[str, int]:
    """各テーブルのCOUNTを取得する"""
    conn = sqlite3.connect(db_path)
    try:
        counts = {}
        for table in HEALTH_CHECK_TABLES:
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # テーブルが存在しない場合はスキップ
                counts[table] = 0
        return counts
    finally:
        conn.close()


def _get_latest_json(snapshot_dir: Path) -> dict | None:
    """最新のメタデータJSONを読み込む。なければNone。"""
    if not snapshot_dir.exists():
        return None

    json_files = sorted(snapshot_dir.glob(f"{SNAPSHOT_PREFIX}*{SNAPSHOT_JSON_SUFFIX}"), reverse=True)
    if not json_files:
        return None

    try:
        return json.loads(json_files[0].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def health_check(db_path: str, snapshot_dir: Path | None = None, threshold: int | None = None) -> HealthCheckResult:
    """最新JSONと現在の行数を比較してヘルスチェックを行う。

    threshold件以上の減少があるテーブルを異常と判定する。
    """
    from src.config import SNAPSHOT_ANOMALY_THRESHOLD

    if snapshot_dir is None:
        snapshot_dir = _get_snapshot_dir(db_path)
    if threshold is None:
        threshold = SNAPSHOT_ANOMALY_THRESHOLD

    current_counts = get_row_counts(db_path)
    result = HealthCheckResult(current_counts=current_counts)

    latest_json = _get_latest_json(snapshot_dir)
    if latest_json is None:
        # 初回起動（スナップショットなし）: 正常扱い
        return result

    prev_counts = latest_json.get("row_counts", {})
    result.previous_counts = prev_counts

    for table in HEALTH_CHECK_TABLES:
        prev = prev_counts.get(table, 0)
        current = current_counts.get(table, 0)
        diff = prev - current
        if diff >= threshold:
            result.is_healthy = False
            result.warnings.append(
                f"- {table}: {prev} → {current} (-{diff}件)"
            )

    return result


def should_take_snapshot(snapshot_dir: Path | None = None, interval_hours: int | None = None, db_path: str | None = None) -> bool:
    """最新JSONのcreated_atで間隔チェック。取得すべきならTrue。"""
    from src.config import SNAPSHOT_INTERVAL_HOURS

    if interval_hours is None:
        interval_hours = SNAPSHOT_INTERVAL_HOURS

    if snapshot_dir is None:
        if db_path is None:
            return True
        snapshot_dir = _get_snapshot_dir(db_path)

    latest_json = _get_latest_json(snapshot_dir)
    if latest_json is None:
        # スナップショットなし: 即取得
        return True

    created_at_str = latest_json.get("created_at")
    if not created_at_str:
        return True

    try:
        created_at = datetime.fromisoformat(created_at_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        elapsed_hours = (now - created_at).total_seconds() / 3600
        return elapsed_hours >= interval_hours
    except (ValueError, TypeError):
        return True


def take_snapshot(db_path: str, snapshot_dir: Path | None = None, max_snapshots: int | None = None) -> Path:
    """sqlite3.backup()でスナップショットを取得し、メタデータJSONを保存する。

    ローテーション: max_snapshots超過時に古いペア(.db + .json)を削除する。
    """
    from src.config import SNAPSHOT_MAX_COUNT

    if snapshot_dir is None:
        snapshot_dir = _get_snapshot_dir(db_path)
    if max_snapshots is None:
        max_snapshots = SNAPSHOT_MAX_COUNT

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M")
    stem = f"{SNAPSHOT_PREFIX}{timestamp}"

    snapshot_db_path = snapshot_dir / f"{stem}{SNAPSHOT_DB_SUFFIX}"
    snapshot_json_path = snapshot_dir / f"{stem}{SNAPSHOT_JSON_SUFFIX}"

    # sqlite3.backup()でスナップショット取得
    source = sqlite3.connect(db_path)
    try:
        dest = sqlite3.connect(str(snapshot_db_path))
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()

    # メタデータJSON保存
    row_counts = get_row_counts(db_path)
    metadata = {
        "created_at": now.isoformat(),
        "db_size_bytes": snapshot_db_path.stat().st_size,
        "row_counts": row_counts,
    }
    snapshot_json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    # ローテーション: 古いスナップショットを削除
    _rotate_snapshots(snapshot_dir, max_snapshots)

    return snapshot_db_path


def _rotate_snapshots(snapshot_dir: Path, max_snapshots: int) -> None:
    """max_snapshots超過時に古い.db + .jsonペアを削除する。"""
    db_files = sorted(snapshot_dir.glob(f"{SNAPSHOT_PREFIX}*{SNAPSHOT_DB_SUFFIX}"))
    while len(db_files) > max_snapshots:
        oldest_db = db_files.pop(0)
        oldest_json = oldest_db.with_suffix(SNAPSHOT_JSON_SUFFIX)
        oldest_db.unlink(missing_ok=True)
        oldest_json.unlink(missing_ok=True)


def restore_snapshot(snapshot_path: str, db_path: str | None = None) -> None:
    """スナップショットからDBを復元する。

    db_pathが未指定の場合はCCM_DB_PATHまたはデフォルトパスから解決する。
    """
    from src.db import get_db_path

    if db_path is None:
        db_path = get_db_path()

    snapshot_file = Path(snapshot_path)
    if not snapshot_file.exists():
        raise FileNotFoundError(f"スナップショットが見つかりません: {snapshot_path}")

    # スナップショットからDBに復元（sqlite3.backup()を使用）
    source = sqlite3.connect(str(snapshot_file))
    try:
        dest = sqlite3.connect(db_path)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()


def main() -> None:
    """CLI: restore サブコマンド"""
    if len(sys.argv) < 3 or sys.argv[1] != "restore":
        print("Usage: python scripts/snapshot.py restore <snapshot_db_path>", file=sys.stderr)
        sys.exit(1)

    snapshot_path = sys.argv[2]
    try:
        restore_snapshot(snapshot_path)
        print(f"復元完了: {snapshot_path}")
    except Exception as e:
        print(f"復元エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
