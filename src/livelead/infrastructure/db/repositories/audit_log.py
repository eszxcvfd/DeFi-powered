"""Audit-log persistence repository (US-026)."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import AuditEntryRow


class AuditEntryRepository:
    """Append-only repository. Update/delete methods intentionally absent."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: AuditEntryRow) -> AuditEntryRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_for_org(
        self, entry_id: UUID, organization_id: UUID
    ) -> AuditEntryRow | None:
        r = await self._session.execute(
            select(AuditEntryRow).where(
                and_(
                    AuditEntryRow.id == str(entry_id),
                    AuditEntryRow.organization_id == str(organization_id),
                )
            )
        )
        return r.scalar_one_or_none()

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        actor_id: str | None = None,
        actor_type: str | None = None,
        action: str | None = None,
        action_family: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        outcome: str | None = None,
        request_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditEntryRow], int]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))

        filters = [AuditEntryRow.organization_id == str(organization_id)]
        if actor_id:
            filters.append(AuditEntryRow.actor_id == actor_id)
        if actor_type:
            filters.append(AuditEntryRow.actor_type == actor_type)
        if action:
            filters.append(AuditEntryRow.action == action)
        if action_family:
            filters.append(AuditEntryRow.action_family == action_family)
        if target_type:
            filters.append(AuditEntryRow.target_type == target_type)
        if target_id:
            filters.append(AuditEntryRow.target_id == target_id)
        if outcome:
            filters.append(AuditEntryRow.outcome == outcome)
        if request_id:
            filters.append(AuditEntryRow.request_id == request_id)
        if since is not None:
            filters.append(AuditEntryRow.occurred_at >= since)
        if until is not None:
            filters.append(AuditEntryRow.occurred_at <= until)

        where = and_(*filters)

        total = (
            await self._session.execute(
                select(func.count(AuditEntryRow.id)).where(where)
            )
        ).scalar_one()

        rows = (
            await self._session.execute(
                select(AuditEntryRow)
                .where(where)
                .order_by(desc(AuditEntryRow.occurred_at), desc(AuditEntryRow.id))
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return list(rows), int(total)

    @staticmethod
    def metadata_json(row: AuditEntryRow) -> dict:
        try:
            value = json.loads(row.metadata_json or "{}")
        except (TypeError, ValueError):
            value = {}
        return value if isinstance(value, dict) else {}
