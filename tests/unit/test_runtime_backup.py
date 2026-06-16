"""Unit tests for the backup-snapshot service (US-040)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.runtime.backups import (
    BackupService,
    BackupServiceError,
)
from livelead.domain.runtime.enums import (
    BackupFreshness,
    BackupVerificationStatus,
)


@pytest.fixture
def service(session: AsyncSession) -> BackupService:
    return BackupService(
        session,
        audit_service=AuditService(session),
        backup_max_age_hours=24.0,
    )


@pytest.mark.asyncio
async def test_record_snapshot_rejects_empty_ids(
    service: BackupService, session: AsyncSession
):
    with pytest.raises(BackupServiceError):
        await service.record_snapshot(
            organization_id="00000000-0000-4000-8000-000000000001",
            backup_id="",
            database_path="data/x",
        )
    with pytest.raises(BackupServiceError):
        await service.record_snapshot(
            organization_id="00000000-0000-4000-8000-000000000001",
            backup_id="ok",
            database_path="",
        )


@pytest.mark.asyncio
async def test_record_snapshot_persists_metadata_and_audits(
    service: BackupService, session: AsyncSession
):
    org_id = "00000000-0000-4000-8000-000000000001"
    snap = await service.record_snapshot(
        organization_id=org_id,
        backup_id="backup-001",
        database_path="data/livelead.sqlite3",
        notes="nightly",
        actor="ops",
        actor_role="owner",
    )
    await session.commit()
    assert snap.backup_id == "backup-001"
    assert snap.verification_status == BackupVerificationStatus.RECORDED
    summary = await service.latest_summary()
    assert summary is not None
    assert summary.snapshot.backup_id == "backup-001"
    audit = AuditService(session)
    entries, _ = await audit.list_entries(
        org_id, action="backup.snapshot.recorded", limit=10
    )
    assert entries and entries[0].action.value == "backup.snapshot.recorded"


@pytest.mark.asyncio
async def test_verify_snapshot_updates_status_and_audits(
    service: BackupService, session: AsyncSession
):
    org_id = "00000000-0000-4000-8000-000000000001"
    await service.record_snapshot(
        organization_id=org_id,
        backup_id="backup-002",
        database_path="data/livelead.sqlite3",
    )
    await session.commit()
    snap = await service.verify_snapshot(
        organization_id=org_id,
        backup_id="backup-002",
        status=BackupVerificationStatus.VERIFIED_RESTORE,
        actor="ops",
        actor_role="owner",
    )
    await session.commit()
    assert snap.verification_status == BackupVerificationStatus.VERIFIED_RESTORE


@pytest.mark.asyncio
async def test_verify_snapshot_marks_failed_status(
    service: BackupService, session: AsyncSession
):
    org_id = "00000000-0000-4000-8000-000000000001"
    await service.record_snapshot(
        organization_id=org_id,
        backup_id="backup-003",
        database_path="data/livelead.sqlite3",
    )
    await session.commit()
    snap = await service.verify_snapshot(
        organization_id=org_id,
        backup_id="backup-003",
        status=BackupVerificationStatus.FAILED_RESTORE,
        actor="ops",
        actor_role="owner",
    )
    await session.commit()
    assert snap.verification_status == BackupVerificationStatus.FAILED_RESTORE


@pytest.mark.asyncio
async def test_verify_snapshot_rejects_unknown_id(
    service: BackupService, session: AsyncSession
):
    with pytest.raises(BackupServiceError):
        await service.verify_snapshot(
            organization_id="00000000-0000-4000-8000-000000000001",
            backup_id="missing",
            status=BackupVerificationStatus.VERIFIED_RESTORE,
        )


@pytest.mark.asyncio
async def test_fresh_snapshot_count_counts_recorded_and_verified(
    service: BackupService, session: AsyncSession
):
    org_id = "00000000-0000-4000-8000-000000000001"
    await service.record_snapshot(
        organization_id=org_id,
        backup_id="backup-010",
        database_path="data/livelead.sqlite3",
    )
    await service.record_snapshot(
        organization_id=org_id,
        backup_id="backup-011",
        database_path="data/livelead.sqlite3",
    )
    await service.record_snapshot(
        organization_id=org_id,
        backup_id="backup-012",
        database_path="data/livelead.sqlite3",
    )
    await session.commit()
    await service.verify_snapshot(
        organization_id=org_id,
        backup_id="backup-011",
        status=BackupVerificationStatus.FAILED_RESTORE,
        actor="ops",
        actor_role="owner",
    )
    await session.commit()
    fresh = await service.fresh_snapshot_count()
    total = await service.total_snapshot_count()
    assert fresh == 2  # recorded + recorded (the failed one is not fresh)
    assert total == 3
