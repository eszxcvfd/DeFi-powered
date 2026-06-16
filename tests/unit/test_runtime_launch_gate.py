"""Unit tests for the launch-gate evaluator (US-040)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from livelead.domain.runtime.enums import (
    BackupFreshness,
    BackupVerificationStatus,
    EnvironmentMode,
    LaunchGateSeverity,
)
from livelead.domain.runtime.gate import (
    DEV_SECRET_MASTER_KEY_PLACEHOLDER,
    check_auth_cookie_secure,
    check_auth_dev_headers,
    check_backup,
    check_redis,
    check_secret_master_key,
    check_sqlite,
    check_worker_heartbeat,
    evaluate_launch_gate,
    summarize_gate,
)
from livelead.domain.runtime.models import (
    BackupSnapshot,
    WorkerHeartbeat,
)


def _backup(age_hours: float = 1.0) -> BackupSnapshot:
    return BackupSnapshot(
        backup_id="backup-1",
        created_at=datetime.now(UTC) - timedelta(hours=age_hours),
        database_path="data/livelead.sqlite3",
        database_size_bytes=1024,
        verification_status=BackupVerificationStatus.RECORDED,
    )


def _heartbeat(age_seconds: float = 5.0) -> WorkerHeartbeat:
    return WorkerHeartbeat(
        worker_id="w1",
        last_seen=datetime.now(UTC) - timedelta(seconds=age_seconds),
    )


def test_check_auth_dev_headers_blocks_when_allowed():
    check = check_auth_dev_headers(auth_allow_dev_headers=True)
    assert check.severity == LaunchGateSeverity.BLOCKING
    assert "dev" in check.name


def test_check_auth_dev_headers_passes_when_disallowed():
    check = check_auth_dev_headers(auth_allow_dev_headers=False)
    assert check.severity == LaunchGateSeverity.OK


def test_check_auth_cookie_secure_is_warning_only():
    off = check_auth_cookie_secure(auth_cookie_secure=False)
    assert off.severity == LaunchGateSeverity.WARNING
    on = check_auth_cookie_secure(auth_cookie_secure=True)
    assert on.severity == LaunchGateSeverity.OK


def test_check_secret_master_key_blocks_default():
    check = check_secret_master_key(secret_master_key=DEV_SECRET_MASTER_KEY_PLACEHOLDER)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_secret_master_key_passes_with_custom_key():
    check = check_secret_master_key(secret_master_key="not-the-default-key")
    assert check.severity == LaunchGateSeverity.OK


def test_check_sqlite_ok_when_writable():
    check = check_sqlite(sqlite_writable=True, sqlite_path="data/x.sqlite3")
    assert check.severity == LaunchGateSeverity.OK


def test_check_sqlite_blocks_when_not_writable():
    check = check_sqlite(sqlite_writable=False, sqlite_path="data/x.sqlite3")
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_redis_passes_when_reachable():
    check = check_redis(redis_reachable=True)
    assert check.severity == LaunchGateSeverity.OK


def test_check_redis_blocks_when_unreachable():
    check = check_redis(redis_reachable=False)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_worker_heartbeat_blocks_when_missing():
    check = check_worker_heartbeat(heartbeat=None, max_age_seconds=300)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_worker_heartbeat_blocks_when_stale():
    check = check_worker_heartbeat(heartbeat=_heartbeat(age_seconds=600), max_age_seconds=300)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_worker_heartbeat_passes_when_recent():
    check = check_worker_heartbeat(heartbeat=_heartbeat(age_seconds=5), max_age_seconds=300)
    assert check.severity == LaunchGateSeverity.OK


def test_check_backup_blocks_when_missing():
    check = check_backup(last_backup=None, max_age_hours=24)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_backup_blocks_when_stale():
    stale = _backup(age_hours=48)
    check = check_backup(last_backup=stale, max_age_hours=24)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_backup_blocks_when_failed_restore():
    snap = BackupSnapshot(
        backup_id="b1",
        created_at=datetime.now(UTC),
        database_path="x",
        database_size_bytes=0,
        verification_status=BackupVerificationStatus.FAILED_RESTORE,
    )
    check = check_backup(last_backup=snap, max_age_hours=24)
    assert check.severity == LaunchGateSeverity.BLOCKING


def test_check_backup_passes_when_fresh_and_recorded():
    check = check_backup(last_backup=_backup(age_hours=1), max_age_hours=24)
    assert check.severity == LaunchGateSeverity.OK


def test_evaluate_launch_gate_pilot_live_blocks_with_unsafe_settings():
    report = evaluate_launch_gate(
        environment_mode=EnvironmentMode.PILOT_LIVE,
        auth_allow_dev_headers=True,
        auth_cookie_secure=True,
        secret_master_key="custom",
        sqlite_writable=True,
        sqlite_path="data/x.sqlite3",
        redis_reachable=True,
        heartbeat=_heartbeat(age_seconds=2),
        backup_max_age_hours=24,
        heartbeat_max_age_seconds=300,
        last_backup=_backup(age_hours=1),
    )
    assert not report.passed
    names = [c.name for c in report.blocking_checks]
    assert "auth.dev_headers_disabled" in names


def test_evaluate_launch_gate_test_like_relaxes_blocking_to_warning():
    report = evaluate_launch_gate(
        environment_mode=EnvironmentMode.TEST_LIKE,
        auth_allow_dev_headers=True,
        auth_cookie_secure=False,
        secret_master_key=DEV_SECRET_MASTER_KEY_PLACEHOLDER,
        sqlite_writable=False,
        sqlite_path="data/x.sqlite3",
        redis_reachable=False,
        heartbeat=None,
        backup_max_age_hours=24,
        heartbeat_max_age_seconds=300,
        last_backup=None,
    )
    # In test_like, blocking conditions become warnings so operators still
    # see the issues but the system remains usable.
    assert report.passed
    assert report.warning_checks
    for c in report.warning_checks:
        assert c.severity == LaunchGateSeverity.WARNING


def test_evaluate_launch_gate_pilot_live_passes_when_safe():
    report = evaluate_launch_gate(
        environment_mode=EnvironmentMode.PILOT_LIVE,
        auth_allow_dev_headers=False,
        auth_cookie_secure=True,
        secret_master_key="rotated-key",
        sqlite_writable=True,
        sqlite_path="data/x.sqlite3",
        redis_reachable=True,
        heartbeat=_heartbeat(age_seconds=2),
        backup_max_age_hours=24,
        heartbeat_max_age_seconds=300,
        last_backup=_backup(age_hours=1),
    )
    assert report.passed


def test_summarize_gate_mentions_first_blocker():
    report = evaluate_launch_gate(
        environment_mode=EnvironmentMode.PILOT_LIVE,
        auth_allow_dev_headers=True,
        auth_cookie_secure=True,
        secret_master_key="custom",
        sqlite_writable=True,
        sqlite_path="data/x.sqlite3",
        redis_reachable=True,
        heartbeat=_heartbeat(age_seconds=2),
        backup_max_age_hours=24,
        heartbeat_max_age_seconds=300,
        last_backup=_backup(age_hours=1),
    )
    summary = summarize_gate(report)
    assert "auth.dev_headers_disabled" in summary
