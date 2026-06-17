"""Backup and restore enums (US-043).

Closed enumerations for the bounded restore, retention
prune, and data-deletion paths. The values are persisted
as strings so the migration can use stable SQL `VARCHAR`
columns; the application layer normalises back to these
enums at the boundary.
"""

from __future__ import annotations

from enum import StrEnum


class RestoreRunStatus(StrEnum):
    """Lifecycle of a single restore attempt.

    The restore rehearsal actor transitions
    `pending` -> `succeeded` when the dry-run
    integrity check passes, or to `failed` /
    `sanitizer_rejected` when the run is
    rejected.
    """

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SANITIZER_REJECTED = "sanitizer_rejected"


class RestoreMode(StrEnum):
    """Mode of a restore run.

    `dry_run` writes to a scratch location; `rehearsal`
    is the same code path executed from the worker
    queue; `production` overwrites the production
    database and requires the application to be in
    `paused` mode from `US-040`.
    """

    DRY_RUN = "dry_run"
    REHEARSAL = "rehearsal"
    PRODUCTION = "production"


class DataDeletionTarget(StrEnum):
    """Closed set of targets for the data-deletion path.

    The first slice supports lead, user, and source
    observation deletion. Tenant-level cascading
    delete is a follow-on story.
    """

    LEAD = "lead"
    USER = "user"
    OBSERVATION = "observation"


SUPPORTED_RESTORE_RUN_STATUSES: frozenset[RestoreRunStatus] = frozenset(
    RestoreRunStatus
)
SUPPORTED_RESTORE_MODES: frozenset[RestoreMode] = frozenset(RestoreMode)
SUPPORTED_DATA_DELETION_TARGETS: frozenset[DataDeletionTarget] = frozenset(
    DataDeletionTarget
)

# Default retention floor that follows `NFR-SEC-008` (90
# days audit retention).
DEFAULT_AUDIT_RETENTION_DAYS: int = 90
MIN_AUDIT_RETENTION_DAYS: int = 90

# Default backup retention (operator-tunable).
DEFAULT_BACKUP_RETENTION_DAYS: int = 30
MIN_BACKUP_RETENTION_DAYS: int = 1
MAX_BACKUP_RETENTION_DAYS: int = 3650  # 10 years


__all__ = [
    "DEFAULT_AUDIT_RETENTION_DAYS",
    "DEFAULT_BACKUP_RETENTION_DAYS",
    "DataDeletionTarget",
    "MAX_BACKUP_RETENTION_DAYS",
    "MIN_AUDIT_RETENTION_DAYS",
    "MIN_BACKUP_RETENTION_DAYS",
    "RestoreMode",
    "RestoreRunStatus",
    "SUPPORTED_DATA_DELETION_TARGETS",
    "SUPPORTED_RESTORE_MODES",
    "SUPPORTED_RESTORE_RUN_STATUSES",
]
