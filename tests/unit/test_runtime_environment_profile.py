"""Unit tests for runtime domain models and freshness rules (US-040)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from livelead.domain.runtime.enums import (
    BackupFreshness,
    BackupVerificationStatus,
    CutoverAction,
    EnvironmentMode,
    LaunchGateSeverity,
    LiveIntegration,
    LiveToggleState,
)
from livelead.domain.runtime.models import (
    BackupSnapshot,
    CutoverEvent,
    EnvironmentProfile,
    LaunchGateCheck,
    LaunchGateReport,
    LiveIntegrationToggle,
    WorkerHeartbeat,
)


def test_backup_snapshot_freshness_classification():
    snap = BackupSnapshot(
        backup_id="b1",
        created_at=datetime.now(UTC) - timedelta(hours=1),
        database_path="x",
        database_size_bytes=0,
        verification_status=BackupVerificationStatus.RECORDED,
    )
    assert snap.freshness(max_age_hours=24) == BackupFreshness.FRESH
    stale = BackupSnapshot(
        backup_id="b2",
        created_at=datetime.now(UTC) - timedelta(hours=72),
        database_path="x",
        database_size_bytes=0,
        verification_status=BackupVerificationStatus.RECORDED,
    )
    assert stale.freshness(max_age_hours=24) == BackupFreshness.STALE
    failed = BackupSnapshot(
        backup_id="b3",
        created_at=datetime.now(UTC),
        database_path="x",
        database_size_bytes=0,
        verification_status=BackupVerificationStatus.FAILED_RESTORE,
    )
    assert failed.freshness(max_age_hours=24) == BackupFreshness.STALE


def test_backup_snapshot_to_dict_is_json_safe():
    snap = BackupSnapshot(
        backup_id="b1",
        created_at=datetime.now(UTC),
        database_path="data/livelead.sqlite3",
        database_size_bytes=2048,
        verification_status=BackupVerificationStatus.VERIFIED_RESTORE,
        notes="restored to staging",
        recorded_by="ops",
    )
    payload = snap.to_dict()
    assert payload["backup_id"] == "b1"
    assert payload["verification_status"] == "verified_restore"


def test_launch_gate_report_passes_when_no_blockers():
    check_ok = LaunchGateCheck(name="x", severity=LaunchGateSeverity.OK)
    report = LaunchGateReport(
        checks=(check_ok,),
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert report.passed
    assert report.blocking_checks == ()


def test_launch_gate_report_blocks_when_blocking_present():
    report = LaunchGateReport(
        checks=(
            LaunchGateCheck(name="a", severity=LaunchGateSeverity.OK),
            LaunchGateCheck(name="b", severity=LaunchGateSeverity.BLOCKING, detail="bad"),
        ),
    )
    assert not report.passed
    assert {c.name for c in report.blocking_checks} == {"b"}


def test_launch_gate_report_to_dict_exposes_blocking_warnings():
    report = LaunchGateReport(
        checks=(
            LaunchGateCheck(name="a", severity=LaunchGateSeverity.OK, detail="ok"),
            LaunchGateCheck(name="b", severity=LaunchGateSeverity.WARNING, detail="warn"),
            LaunchGateCheck(name="c", severity=LaunchGateSeverity.BLOCKING, detail="bad"),
        )
    )
    payload = report.to_dict()
    assert payload["passed"] is False
    assert payload["blocking"] == [{"name": "c", "detail": "bad"}]
    assert payload["warnings"] == [{"name": "b", "detail": "warn"}]
    assert {c["name"] for c in payload["checks"]} == {"a", "b", "c"}


def test_live_integration_toggle_defaults_to_disabled():
    toggle = LiveIntegrationToggle(integration=LiveIntegration.DISCOVERY)
    assert toggle.state == LiveToggleState.DISABLED
    assert not toggle.is_enabled


def test_worker_heartbeat_age_seconds_is_non_negative():
    hb = WorkerHeartbeat(
        worker_id="w",
        last_seen=datetime.now(UTC) - timedelta(seconds=10),
    )
    assert 0.0 <= hb.age_seconds <= 60.0


def test_cutover_event_to_dict_round_trip():
    event = CutoverEvent(
        event_id="e1",
        action=CutoverAction.ENTER_PILOT_LIVE,
        previous_mode=EnvironmentMode.TEST_LIKE,
        new_mode=EnvironmentMode.PILOT_LIVE,
        actor="ops",
        reason="first go-live",
        occurred_at=datetime.now(UTC),
        gate_passed=True,
        gate_summary="launch gate passed",
    )
    payload = event.to_dict()
    assert payload["action"] == "enter_pilot_live"
    assert payload["new_mode"] == "pilot_live"
    assert payload["gate_passed"] is True


def test_environment_profile_to_dict_includes_everything():
    profile = EnvironmentProfile(
        mode=EnvironmentMode.PILOT_LIVE,
        gate=LaunchGateReport(),
        auth_allow_dev_headers=False,
        auth_cookie_secure=True,
        secret_master_key_is_default=False,
        tls_terminated=True,
        redis_reachable=True,
        sqlite_writable=True,
    )
    payload = profile.to_dict()
    assert payload["mode"] == "pilot_live"
    assert payload["auth_allow_dev_headers"] is False
    assert payload["redis_reachable"] is True
