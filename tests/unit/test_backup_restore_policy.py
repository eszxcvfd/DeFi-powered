"""Unit tests for the retention policy validation (US-043)."""

from __future__ import annotations

import pytest

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
from livelead.domain.backup.models import (
    validate_data_deletion_request,
    validate_retention_policy,
)


def test_default_constants_match_spec() -> None:
    assert DEFAULT_BACKUP_RETENTION_DAYS == 30
    assert DEFAULT_AUDIT_RETENTION_DAYS == 90
    assert MIN_AUDIT_RETENTION_DAYS == 90
    assert MIN_BACKUP_RETENTION_DAYS == 1
    assert MAX_BACKUP_RETENTION_DAYS == 3650


def test_validate_retention_policy_accepts_defaults() -> None:
    validate_retention_policy(
        backup_retention_days=DEFAULT_BACKUP_RETENTION_DAYS,
        audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
        prune_enabled=False,
    )


def test_validate_retention_policy_rejects_backup_days_below_floor() -> None:
    with pytest.raises(ValueError) as exc:
        validate_retention_policy(
            backup_retention_days=0,
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            prune_enabled=False,
        )
    assert "backup_retention_days_out_of_range" in str(exc.value)


def test_validate_retention_policy_rejects_backup_days_above_ceiling() -> None:
    with pytest.raises(ValueError) as exc:
        validate_retention_policy(
            backup_retention_days=MAX_BACKUP_RETENTION_DAYS + 1,
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            prune_enabled=False,
        )
    assert "backup_retention_days_out_of_range" in str(exc.value)


def test_validate_retention_policy_rejects_audit_days_below_nfr_floor() -> None:
    with pytest.raises(ValueError) as exc:
        validate_retention_policy(
            backup_retention_days=DEFAULT_BACKUP_RETENTION_DAYS,
            audit_retention_days=MIN_AUDIT_RETENTION_DAYS - 1,
            prune_enabled=False,
        )
    assert "audit_retention_days_below_floor" in str(exc.value)


def test_validate_retention_policy_rejects_non_int() -> None:
    with pytest.raises(ValueError):
        validate_retention_policy(
            backup_retention_days="thirty",  # type: ignore[arg-type]
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            prune_enabled=False,
        )


def test_validate_retention_policy_rejects_non_bool_prune() -> None:
    with pytest.raises(ValueError):
        validate_retention_policy(
            backup_retention_days=DEFAULT_BACKUP_RETENTION_DAYS,
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            prune_enabled="yes",  # type: ignore[arg-type]
        )


def test_validate_data_deletion_request_accepts_minimal_payload() -> None:
    validate_data_deletion_request(
        target=DataDeletionTarget.LEAD,
        target_id="lead-123",
        accepted_by="owner-1",
        reason="GDPR right-to-erasure",
    )


def test_validate_data_deletion_request_rejects_unknown_target() -> None:
    with pytest.raises(ValueError) as exc:
        validate_data_deletion_request(
            target="not_a_target",
            target_id="lead-123",
            accepted_by="owner-1",
            reason="GDPR right-to-erasure",
        )
    assert "target_unsupported" in str(exc.value)


def test_validate_data_deletion_request_rejects_missing_target_id() -> None:
    with pytest.raises(ValueError) as exc:
        validate_data_deletion_request(
            target=DataDeletionTarget.LEAD,
            target_id="",
            accepted_by="owner-1",
            reason="GDPR right-to-erasure",
        )
    assert "target_id_required" in str(exc.value)


def test_validate_data_deletion_request_rejects_missing_accepted_by() -> None:
    with pytest.raises(ValueError) as exc:
        validate_data_deletion_request(
            target=DataDeletionTarget.LEAD,
            target_id="lead-123",
            accepted_by="",
            reason="GDPR right-to-erasure",
        )
    assert "accepted_by_required" in str(exc.value)


def test_validate_data_deletion_request_rejects_missing_reason() -> None:
    with pytest.raises(ValueError) as exc:
        validate_data_deletion_request(
            target=DataDeletionTarget.LEAD,
            target_id="lead-123",
            accepted_by="owner-1",
            reason="",
        )
    assert "reason_required" in str(exc.value)


def test_validate_data_deletion_request_rejects_too_long_reason() -> None:
    with pytest.raises(ValueError) as exc:
        validate_data_deletion_request(
            target=DataDeletionTarget.LEAD,
            target_id="lead-123",
            accepted_by="owner-1",
            reason="a" * 501,
        )
    assert "reason_too_long" in str(exc.value)


def test_restore_run_status_enum_is_closed() -> None:
    values = {s.value for s in RestoreRunStatus}
    assert values == {"pending", "succeeded", "failed", "sanitizer_rejected"}


def test_restore_mode_enum_is_closed() -> None:
    values = {m.value for m in RestoreMode}
    assert values == {"dry_run", "rehearsal", "production"}


def test_data_deletion_target_enum_is_closed() -> None:
    values = {t.value for t in DataDeletionTarget}
    assert values == {"lead", "user", "observation"}
