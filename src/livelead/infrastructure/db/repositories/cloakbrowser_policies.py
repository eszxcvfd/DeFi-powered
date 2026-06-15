"""CloakBrowser policy persistence (US-025)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import CloakBrowserPolicyRow


class CloakBrowserPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_source(
        self, source_id: UUID, organization_id: UUID
    ) -> CloakBrowserPolicyRow | None:
        r = await self._session.execute(
            select(CloakBrowserPolicyRow).where(
                CloakBrowserPolicyRow.source_id == str(source_id),
                CloakBrowserPolicyRow.organization_id == str(organization_id),
            )
        )
        return r.scalar_one_or_none()

    async def upsert_request(
        self,
        *,
        organization_id: UUID,
        source_id: UUID,
        actor: str,
        purpose_rationale: str,
        pinned_version: str | None = None,
        expected_checksum: str | None = None,
    ) -> CloakBrowserPolicyRow:
        row = await self.get_for_source(source_id, organization_id)
        now = datetime.now(UTC)
        if row is None:
            row = CloakBrowserPolicyRow(
                id=str(uuid4()),
                organization_id=str(organization_id),
                source_id=str(source_id),
                purpose_rationale=purpose_rationale.strip(),
                pinned_version=pinned_version,
                expected_checksum=expected_checksum,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.purpose_rationale = purpose_rationale.strip()
            if pinned_version is not None:
                row.pinned_version = pinned_version
            if expected_checksum is not None:
                row.expected_checksum = expected_checksum
            row.revoked_at = None
            row.revoked_by = None
            row.revoke_reason = None
            row.owner_admin_approved = False
            row.compliance_approved = False
            row.owner_admin_actor = None
            row.compliance_actor = None
            row.owner_admin_approved_at = None
            row.compliance_approved_at = None
            row.updated_at = now
        await self._session.flush()
        return row

    async def apply_owner_admin_approval(
        self, row: CloakBrowserPolicyRow, actor: str
    ) -> CloakBrowserPolicyRow:
        now = datetime.now(UTC)
        row.owner_admin_approved = True
        row.owner_admin_actor = actor
        row.owner_admin_approved_at = now
        row.updated_at = now
        await self._session.flush()
        return row

    async def apply_compliance_approval(
        self, row: CloakBrowserPolicyRow, actor: str
    ) -> CloakBrowserPolicyRow:
        now = datetime.now(UTC)
        row.compliance_approved = True
        row.compliance_actor = actor
        row.compliance_approved_at = now
        row.updated_at = now
        await self._session.flush()
        return row

    async def revoke(
        self,
        row: CloakBrowserPolicyRow,
        *,
        actor: str,
        reason: str,
    ) -> CloakBrowserPolicyRow:
        now = datetime.now(UTC)
        row.revoked_at = now
        row.revoked_by = actor
        row.revoke_reason = reason.strip() or "revoked"
        row.owner_admin_approved = False
        row.compliance_approved = False
        row.updated_at = now
        await self._session.flush()
        return row