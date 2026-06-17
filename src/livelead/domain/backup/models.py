"""Backup and restore domain models (US-043).

Pure dataclasses with no I/O. The infrastructure layer
is responsible for translating these to and from
SQLAlchemy rows. The model layer deliberately does
not import SQLAlchemy, FastAPI, or any framework.

The model layer reuses the `BackupSnapshot` model
from `US-040` rather than redefining it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.backup.enums import (
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_BACKUP_RETENTION_DAYS,
    DataDeletionTarget,
    MAX_BACKUP_RETENTION_DAYS,
    MIN_AUDIT_RETENTION_DAYS,
    MIN_BACKUP_RETENTION_DAYS,
    RestoreMode,
    RestoreRunStatus,
)


# ---------------------------------------------------------------------------
# Restore run
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BackupRestoreRun:
    """A single record of a restore attempt (US-043).

    The row carries enough information to prove that a
    backup can be restored within the RTO target from
    `NFR-REL-005`. The `manifest_hash` matches the
    `BackupSnapshot.manifest_hash` when the restore is
    faithful; a mismatch means the integrity check
    failed.
    """

    id: str
    organization_id: str
    backup_id: str
    started_at: datetime
    completed_at: datetime | None
    status: RestoreRunStatus
    mode: RestoreMode
    target_location: str
    manifest_hash: str = ""
    row_count: int = 0
    audit_correlation_id: str = ""
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "backup_id": self.backup_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "status": self.status.value,
            "mode": self.mode.value,
            "target_location": self.target_location,
            "manifest_hash": self.manifest_hash,
            "row_count": int(self.row_count),
            "audit_correlation_id": self.audit_correlation_id,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Restore result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """The result of a single restore attempt.

    Returned synchronously by `dry_run_restore` and
    stored on the `BackupRestoreRun` row.
    """

    backup_id: str
    status: RestoreRunStatus
    target_location: str
    manifest_hash: str
    row_count: int
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "status": self.status.value,
            "target_location": self.target_location,
            "manifest_hash": self.manifest_hash,
            "row_count": int(self.row_count),
            "error": self.error,
            "started_at": (
                self.started_at.isoformat() if self.started_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """A single per-workspace retention policy (US-043).

    The default `audit_retention_days` follows the
    `NFR-SEC-008` floor (90 days) and cannot be
    lowered below the floor. The default
    `backup_retention_days` is 30 days and is
    operator-tunable between 1 and 3650 days.
    """

    organization_id: str
    backup_retention_days: int = DEFAULT_BACKUP_RETENTION_DAYS
    audit_retention_days: int = DEFAULT_AUDIT_RETENTION_DAYS
    prune_enabled: bool = False
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "backup_retention_days": int(self.backup_retention_days),
            "audit_retention_days": int(self.audit_retention_days),
            "prune_enabled": bool(self.prune_enabled),
            "accepted_by": self.accepted_by,
            "accepted_at": (
                self.accepted_at.isoformat() if self.accepted_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Data deletion request
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DataDeletionRequest:
    """A bounded data-deletion request (US-043).

    The request refuses to run without an `accepted_by`
    and a `reason` recorded in the payload. The reason
    is stored on the audit entry and surfaced in the
    operator panel.
    """

    organization_id: str
    target: DataDeletionTarget
    target_id: str
    accepted_by: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "target": self.target.value,
            "target_id": self.target_id,
            "accepted_by": self.accepted_by,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_retention_policy(
    *,
    backup_retention_days: int,
    audit_retention_days: int,
    prune_enabled: bool,
) -> None:
    """Validate a candidate retention policy before it is persisted.

    The validator enforces the `NFR-SEC-008` audit
    retention floor and the operator-tunable
    `backup_retention_days` range. It does not enforce
    acceptance (the REST layer enforces `accepted_by` /
    `accepted_at`); it only checks the configuration
    shape.
    """

    try:
        backup_days = int(backup_retention_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("RETENTION_INVALID:backup_retention_days_not_int") from exc
    if backup_days < MIN_BACKUP_RETENTION_DAYS or backup_days > MAX_BACKUP_RETENTION_DAYS:
        raise ValueError(
            f"RETENTION_INVALID:backup_retention_days_out_of_range:{backup_days}"
        )
    try:
        audit_days = int(audit_retention_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("RETENTION_INVALID:audit_retention_days_not_int") from exc
    if audit_days < MIN_AUDIT_RETENTION_DAYS:
        raise ValueError(
            f"RETENTION_INVALID:audit_retention_days_below_floor:{audit_days}"
        )
    if not isinstance(prune_enabled, bool):
        raise ValueError("RETENTION_INVALID:prune_enabled_not_bool")


def validate_data_deletion_request(
    *,
    target: DataDeletionTarget | str,
    target_id: str,
    accepted_by: str,
    reason: str,
) -> None:
    """Validate a candidate data-deletion request before it runs."""

    if isinstance(target, DataDeletionTarget):
        target_value = target.value
    else:
        target_value = str(target)
    if target_value not in {t.value for t in DataDeletionTarget}:
        raise ValueError(f"RETENTION_INVALID:target_unsupported:{target_value}")
    if not target_id or not target_id.strip():
        raise ValueError("RETENTION_INVALID:target_id_required")
    if not accepted_by or not accepted_by.strip():
        raise ValueError("RETENTION_INVALID:accepted_by_required")
    if not reason or not reason.strip():
        raise ValueError("RETENTION_INVALID:reason_required")
    if len(reason) > 500:
        raise ValueError("RETENTION_INVALID:reason_too_long")


__all__ = [
    "BackupRestoreRun",
    "DataDeletionRequest",
    "RestoreResult",
    "RetentionPolicy",
    "validate_data_deletion_request",
    "validate_retention_policy",
]
