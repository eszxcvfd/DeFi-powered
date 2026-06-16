"""Runtime and live-cutover domain models (US-040).

Pure dataclasses with no I/O. The infrastructure layer is responsible for
translating these to and from SQLAlchemy rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.runtime.enums import (
    BackupFreshness,
    BackupVerificationStatus,
    CutoverAction,
    EnvironmentMode,
    LaunchGateSeverity,
    LiveIntegration,
    LiveToggleState,
)


@dataclass(frozen=True, slots=True)
class LaunchGateCheck:
    """A single launch-gate evaluation result.

    `severity` distinguishes `ok` / `warning` / `blocking`. `blocking` checks
    prevent `pilot_live` entry; `warning` checks are surfaced to operators
    but do not block the gate.
    """

    name: str
    severity: LaunchGateSeverity
    detail: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.severity == LaunchGateSeverity.BLOCKING

    @property
    def is_warning(self) -> bool:
        return self.severity == LaunchGateSeverity.WARNING

    @property
    def is_ok(self) -> bool:
        return self.severity == LaunchGateSeverity.OK


@dataclass(frozen=True, slots=True)
class LaunchGateReport:
    """Aggregate result of the launch-gate evaluation."""

    checks: tuple[LaunchGateCheck, ...] = field(default_factory=tuple)
    evaluated_at: datetime | None = None
    environment_mode: EnvironmentMode = EnvironmentMode.TEST_LIKE

    @property
    def blocking_checks(self) -> tuple[LaunchGateCheck, ...]:
        return tuple(c for c in self.checks if c.is_blocking)

    @property
    def warning_checks(self) -> tuple[LaunchGateCheck, ...]:
        return tuple(c for c in self.checks if c.is_warning)

    @property
    def passed(self) -> bool:
        return not self.blocking_checks

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "environment_mode": self.environment_mode.value,
            "blocking": [
                {"name": c.name, "detail": c.detail} for c in self.blocking_checks
            ],
            "warnings": [
                {"name": c.name, "detail": c.detail} for c in self.warning_checks
            ],
            "checks": [
                {"name": c.name, "severity": c.severity.value, "detail": c.detail}
                for c in self.checks
            ],
        }


@dataclass(frozen=True, slots=True)
class LiveIntegrationToggle:
    """Explicit enablement record for a single live integration."""

    integration: LiveIntegration
    state: LiveToggleState = LiveToggleState.DISABLED
    updated_at: datetime | None = None
    updated_by: str = ""
    approval_note: str = ""
    previous_state: LiveToggleState = LiveToggleState.DISABLED

    @property
    def is_enabled(self) -> bool:
        return self.state == LiveToggleState.ENABLED

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration": self.integration.value,
            "state": self.state.value,
            "previous_state": self.previous_state.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
            "approval_note": self.approval_note,
        }


@dataclass(frozen=True, slots=True)
class BackupSnapshot:
    """A durable record of a backup execution (US-040)."""

    backup_id: str
    created_at: datetime
    database_path: str
    database_size_bytes: int
    verification_status: BackupVerificationStatus
    notes: str = ""
    recorded_by: str = ""
    verified_at: datetime | None = None
    verified_by: str | None = None

    def age_seconds(self, *, now: datetime | None = None) -> float:
        from datetime import UTC

        ref = now or datetime.now(UTC)
        if self.created_at.tzinfo is None:
            from datetime import timezone

            created = self.created_at.replace(tzinfo=timezone.utc)
        else:
            created = self.created_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        return max(0.0, (ref - created).total_seconds())

    def freshness(self, *, max_age_hours: float, now: datetime | None = None) -> BackupFreshness:
        age_h = self.age_seconds(now=now) / 3600.0
        if self.verification_status == BackupVerificationStatus.FAILED_RESTORE:
            return BackupFreshness.STALE
        if age_h <= max_age_hours:
            return BackupFreshness.FRESH
        return BackupFreshness.STALE

    def to_dict(self) -> dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "database_path": self.database_path,
            "database_size_bytes": self.database_size_bytes,
            "verification_status": self.verification_status.value,
            "notes": self.notes,
            "recorded_by": self.recorded_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
        }


@dataclass(frozen=True, slots=True)
class CutoverEvent:
    """A single cutover transition record (US-040)."""

    event_id: str
    action: CutoverAction
    previous_mode: EnvironmentMode
    new_mode: EnvironmentMode
    actor: str
    reason: str
    occurred_at: datetime
    notes: str = ""
    gate_passed: bool = False
    gate_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action": self.action.value,
            "previous_mode": self.previous_mode.value,
            "new_mode": self.new_mode.value,
            "actor": self.actor,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "notes": self.notes,
            "gate_passed": self.gate_passed,
            "gate_summary": self.gate_summary,
        }


@dataclass(frozen=True, slots=True)
class WorkerHeartbeat:
    """Last worker heartbeat record (US-040)."""

    worker_id: str
    last_seen: datetime
    last_task: str = ""
    detail: str = ""

    @property
    def age_seconds(self) -> float:
        from datetime import UTC

        last = self.last_seen
        if last.tzinfo is None:
            from datetime import timezone

            last = last.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(UTC) - last).total_seconds())

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "last_task": self.last_task,
            "detail": self.detail,
            "age_seconds": self.age_seconds,
        }


@dataclass(frozen=True, slots=True)
class EnvironmentProfile:
    """Aggregate read-only view of the live environment (US-040)."""

    mode: EnvironmentMode
    gate: LaunchGateReport
    toggles: tuple[LiveIntegrationToggle, ...] = field(default_factory=tuple)
    last_backup: BackupSnapshot | None = None
    backup_freshness: BackupFreshness = BackupFreshness.UNKNOWN
    worker_heartbeat: WorkerHeartbeat | None = None
    auth_allow_dev_headers: bool = True
    auth_cookie_secure: bool = False
    secret_master_key_is_default: bool = True
    tls_terminated: bool = False
    redis_reachable: bool = False
    sqlite_writable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "gate": self.gate.to_dict(),
            "toggles": [t.to_dict() for t in self.toggles],
            "last_backup": self.last_backup.to_dict() if self.last_backup else None,
            "backup_freshness": self.backup_freshness.value,
            "worker_heartbeat": self.worker_heartbeat.to_dict() if self.worker_heartbeat else None,
            "auth_allow_dev_headers": self.auth_allow_dev_headers,
            "auth_cookie_secure": self.auth_cookie_secure,
            "secret_master_key_is_default": self.secret_master_key_is_default,
            "tls_terminated": self.tls_terminated,
            "redis_reachable": self.redis_reachable,
            "sqlite_writable": self.sqlite_writable,
        }
