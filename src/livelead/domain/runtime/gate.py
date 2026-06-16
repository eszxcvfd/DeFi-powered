"""Launch-gate evaluation (US-040).

Pure functions only. The evaluator returns a `LaunchGateReport` containing
`ok` / `warning` / `blocking` checks. It is invoked by both the application
service (live readiness) and the tests; no I/O is performed here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from livelead.domain.runtime.enums import (
    BackupFreshness,
    EnvironmentMode,
    LaunchGateSeverity,
)
from livelead.domain.runtime.models import (
    BackupSnapshot,
    LaunchGateCheck,
    LaunchGateReport,
    WorkerHeartbeat,
)

# Documented dev placeholder for `LIVELEAD_SECRET_MASTER_KEY`. Live mode must
# override this value.
DEV_SECRET_MASTER_KEY_PLACEHOLDER = "dev-only-change-in-production-livelead"


def check_auth_dev_headers(*, auth_allow_dev_headers: bool) -> LaunchGateCheck:
    return LaunchGateCheck(
        name="auth.dev_headers_disabled",
        severity=(
            LaunchGateSeverity.OK
            if not auth_allow_dev_headers
            else LaunchGateSeverity.BLOCKING
        ),
        detail=(
            "Auth dev headers disabled"
            if not auth_allow_dev_headers
            else "LIVELEAD_AUTH_ALLOW_DEV_HEADERS must be false in live mode"
        ),
    )


def check_auth_cookie_secure(*, auth_cookie_secure: bool) -> LaunchGateCheck:
    return LaunchGateCheck(
        name="auth.cookie_secure",
        severity=(
            LaunchGateSeverity.OK
            if auth_cookie_secure
            else LaunchGateSeverity.WARNING
        ),
        detail=(
            "Session cookie Secure flag enabled"
            if auth_cookie_secure
            else "LIVELEAD_AUTH_COOKIE_SECURE should be true behind TLS"
        ),
    )


def check_secret_master_key(*, secret_master_key: str) -> LaunchGateCheck:
    is_default = secret_master_key == DEV_SECRET_MASTER_KEY_PLACEHOLDER or not secret_master_key
    return LaunchGateCheck(
        name="secrets.master_key_rotated",
        severity=(
            LaunchGateSeverity.BLOCKING if is_default else LaunchGateSeverity.OK
        ),
        detail=(
            "LIVELEAD_SECRET_MASTER_KEY still uses the dev placeholder"
            if is_default
            else "Custom LIVELEAD_SECRET_MASTER_KEY configured"
        ),
    )


def check_sqlite(*, sqlite_writable: bool, sqlite_path: str) -> LaunchGateCheck:
    return LaunchGateCheck(
        name="database.sqlite_writable",
        severity=(
            LaunchGateSeverity.OK
            if sqlite_writable
            else LaunchGateSeverity.BLOCKING
        ),
        detail=(
            f"SQLite writable at {sqlite_path}"
            if sqlite_writable
            else f"SQLite path {sqlite_path} is not writable"
        ),
    )


def check_redis(*, redis_reachable: bool) -> LaunchGateCheck:
    return LaunchGateCheck(
        name="queue.redis_reachable",
        severity=(
            LaunchGateSeverity.OK
            if redis_reachable
            else LaunchGateSeverity.BLOCKING
        ),
        detail=(
            "Redis broker reachable"
            if redis_reachable
            else "Redis broker is unreachable; check LIVELEAD_REDIS_URL"
        ),
    )


def check_worker_heartbeat(
    *,
    heartbeat: WorkerHeartbeat | None,
    max_age_seconds: float,
) -> LaunchGateCheck:
    if heartbeat is None:
        return LaunchGateCheck(
            name="worker.heartbeat_recent",
            severity=LaunchGateSeverity.BLOCKING,
            detail="No worker heartbeat recorded yet",
        )
    age = heartbeat.age_seconds
    if age > max_age_seconds:
        return LaunchGateCheck(
            name="worker.heartbeat_recent",
            severity=LaunchGateSeverity.BLOCKING,
            detail=(
                f"Last worker heartbeat is {age:.0f}s old "
                f"(threshold {max_age_seconds:.0f}s)"
            ),
        )
    return LaunchGateCheck(
        name="worker.heartbeat_recent",
        severity=LaunchGateSeverity.OK,
        detail=f"Worker heartbeat {age:.0f}s ago (worker_id={heartbeat.worker_id})",
    )


def check_backup(
    *,
    last_backup: BackupSnapshot | None,
    max_age_hours: float,
) -> LaunchGateCheck:
    if last_backup is None:
        return LaunchGateCheck(
            name="backup.snapshot_fresh",
            severity=LaunchGateSeverity.BLOCKING,
            detail="No backup snapshot has been recorded yet",
        )
    if last_backup.verification_status.value == "failed_restore":
        return LaunchGateCheck(
            name="backup.snapshot_fresh",
            severity=LaunchGateSeverity.BLOCKING,
            detail="Last backup has a failed_restore status",
        )
    freshness = last_backup.freshness(max_age_hours=max_age_hours)
    if freshness == BackupFreshness.STALE:
        return LaunchGateCheck(
            name="backup.snapshot_fresh",
            severity=LaunchGateSeverity.BLOCKING,
            detail=(
                f"Last backup is older than {max_age_hours:.0f}h "
                f"(backup_id={last_backup.backup_id})"
            ),
        )
    return LaunchGateCheck(
        name="backup.snapshot_fresh",
        severity=LaunchGateSeverity.OK,
        detail=(
            f"Backup {last_backup.backup_id} is fresh "
            f"({last_backup.verification_status.value})"
        ),
    )


def evaluate_launch_gate(
    *,
    environment_mode: EnvironmentMode,
    auth_allow_dev_headers: bool,
    auth_cookie_secure: bool,
    secret_master_key: str,
    sqlite_writable: bool,
    sqlite_path: str,
    redis_reachable: bool,
    heartbeat: WorkerHeartbeat | None,
    backup_max_age_hours: float,
    heartbeat_max_age_seconds: float,
    last_backup: BackupSnapshot | None = None,
    now: datetime | None = None,
) -> LaunchGateReport:
    """Return a `LaunchGateReport` describing whether the environment is
    ready for `pilot_live` entry.

    In `test_like` mode, only the auth-dev-headers check is treated as a hard
    block (operators are not required to meet the live gate to keep working
    in test mode). All other checks run for visibility.
    """

    checks: list[LaunchGateCheck] = []
    checks.append(
        check_auth_dev_headers(auth_allow_dev_headers=auth_allow_dev_headers)
    )
    checks.append(
        check_auth_cookie_secure(auth_cookie_secure=auth_cookie_secure)
    )
    checks.append(
        check_secret_master_key(secret_master_key=secret_master_key)
    )
    checks.append(
        check_sqlite(sqlite_writable=sqlite_writable, sqlite_path=sqlite_path)
    )
    checks.append(check_redis(redis_reachable=redis_reachable))
    checks.append(
        check_worker_heartbeat(
            heartbeat=heartbeat, max_age_seconds=heartbeat_max_age_seconds
        )
    )
    checks.append(
        check_backup(
            last_backup=last_backup, max_age_hours=backup_max_age_hours
        )
    )

    if environment_mode == EnvironmentMode.TEST_LIKE:
        # Operators staying in test mode do not need the live gate to pass;
        # warnings remain visible. Demote blocking to warning so the report
        # still surfaces real issues without forcing a rollout.
        relaxed: list[LaunchGateCheck] = []
        for c in checks:
            if c.severity == LaunchGateSeverity.BLOCKING:
                relaxed.append(
                    LaunchGateCheck(
                        name=c.name,
                        severity=LaunchGateSeverity.WARNING,
                        detail=f"{c.detail} (test_like mode: not blocking)",
                    )
                )
            else:
                relaxed.append(c)
        checks = relaxed

    return LaunchGateReport(
        checks=tuple(checks),
        evaluated_at=now or datetime.now(UTC),
        environment_mode=environment_mode,
    )


def summarize_gate(report: LaunchGateReport) -> str:
    """Short human-readable summary used in cutover events and audit logs."""

    if report.passed:
        return "launch gate passed"
    names = ", ".join(c.name for c in report.blocking_checks)
    return f"launch gate blocked by: {names}"


def gate_to_safe_payload(report: LaunchGateReport) -> dict[str, Any]:
    """Project a gate report to a payload safe to log or return.

    The payload never includes connection strings, secret values, or full
    filesystem paths beyond the configured SQLite path name.
    """

    return report.to_dict()
