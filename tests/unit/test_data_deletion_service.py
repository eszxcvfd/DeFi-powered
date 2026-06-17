"""Unit tests for the data deletion service (US-043)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.backup_restore import (
    BackupRestoreError,
    DataDeletionService,
)
from livelead.domain.backup.enums import DataDeletionTarget


@pytest.mark.asyncio
async def test_data_deletion_rejects_missing_accepted_by(session: AsyncSession):
    service = DataDeletionService(session)
    with pytest.raises(BackupRestoreError) as exc:
        await service.delete_data(
            organization_id="00000000-0000-4000-8000-000000000001",
            target=DataDeletionTarget.LEAD,
            target_id="lead-123",
            accepted_by="",
            reason="GDPR right-to-erasure",
        )
    assert "accepted_by_required" in str(exc.value)


@pytest.mark.asyncio
async def test_data_deletion_rejects_missing_reason(session: AsyncSession):
    service = DataDeletionService(session)
    with pytest.raises(BackupRestoreError) as exc:
        await service.delete_data(
            organization_id="00000000-0000-4000-8000-000000000001",
            target=DataDeletionTarget.LEAD,
            target_id="lead-123",
            accepted_by="owner-1",
            reason="",
        )
    assert "reason_required" in str(exc.value)


@pytest.mark.asyncio
async def test_data_deletion_rejects_unknown_target(session: AsyncSession):
    service = DataDeletionService(session)
    with pytest.raises(BackupRestoreError) as exc:
        await service.delete_data(
            organization_id="00000000-0000-4000-8000-000000000001",
            target="not_a_target",
            target_id="lead-123",
            accepted_by="owner-1",
            reason="GDPR right-to-erasure",
        )
    assert "target_unsupported" in str(exc.value)


@pytest.mark.asyncio
async def test_data_deletion_rejects_missing_lead(session: AsyncSession):
    service = DataDeletionService(session)
    with pytest.raises(BackupRestoreError) as exc:
        await service.delete_data(
            organization_id="00000000-0000-4000-8000-000000000001",
            target=DataDeletionTarget.LEAD,
            target_id="missing-lead",
            accepted_by="owner-1",
            reason="GDPR right-to-erasure",
        )
    assert "LEAD_NOT_FOUND" in str(exc.value)


@pytest.mark.asyncio
async def test_data_deletion_rejects_missing_user(session: AsyncSession):
    service = DataDeletionService(session)
    with pytest.raises(BackupRestoreError) as exc:
        await service.delete_data(
            organization_id="00000000-0000-4000-8000-000000000001",
            target=DataDeletionTarget.USER,
            target_id="missing-user",
            accepted_by="owner-1",
            reason="GDPR right-to-erasure",
        )
    assert "USER_NOT_FOUND" in str(exc.value)


@pytest.mark.asyncio
async def test_data_deletion_rejects_missing_observation(session: AsyncSession):
    service = DataDeletionService(session)
    with pytest.raises(BackupRestoreError) as exc:
        await service.delete_data(
            organization_id="00000000-0000-4000-8000-000000000001",
            target=DataDeletionTarget.OBSERVATION,
            target_id="missing-observation",
            accepted_by="owner-1",
            reason="GDPR right-to-erasure",
        )
    assert "OBSERVATION_NOT_FOUND" in str(exc.value)
