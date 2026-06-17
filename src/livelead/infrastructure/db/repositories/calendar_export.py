"""Event calendar export persistence repositories (US-045).

The repository owns every read and write for
``calendar_export_tokens`` and ``calendar_export_audits``. All
methods take ``organization_id`` first so tenant isolation is
mandatory at the data layer. The repository deliberately
returns pure dataclasses from
``livelead.domain.calendar_export.models``; the application
service is the only place that knows the secret-safe payload
contract and the audit entry shape.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.calendar_export.enums import (
    CalendarExportResult,
    CalendarScope,
)
from livelead.domain.calendar_export.models import (
    CalendarExportAudit,
    CalendarExportToken,
)
from livelead.infrastructure.db.calendar_export_mappers import (
    row_to_calendar_export_audit,
    row_to_calendar_export_token,
)
from livelead.infrastructure.db.models import (
    CalendarExportAuditRow,
    CalendarExportTokenRow,
)

logger = logging.getLogger("livelead.calendar_export_repo")


def _now() -> datetime:
    return datetime.utcnow()


def _serialize_filter(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return json.dumps(value, default=str, sort_keys=True)


# ---------------------------------------------------------------------------
# Token repository
# ---------------------------------------------------------------------------


class CalendarExportTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_for_org(
        self, organization_id: UUID | str, token_id: UUID | str
    ) -> CalendarExportToken | None:
        result = await self._session.execute(
            select(CalendarExportTokenRow).where(
                and_(
                    CalendarExportTokenRow.id == str(token_id),
                    CalendarExportTokenRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_calendar_export_token(row) if row else None

    async def get_by_hash(
        self, organization_id: UUID | str, token_hash: str
    ) -> CalendarExportToken | None:
        result = await self._session.execute(
            select(CalendarExportTokenRow).where(
                and_(
                    CalendarExportTokenRow.organization_id == str(organization_id),
                    CalendarExportTokenRow.token_hash == token_hash,
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_calendar_export_token(row) if row else None

    async def list_for_user(
        self,
        organization_id: UUID | str,
        user_id: UUID | str,
        *,
        include_revoked: bool = False,
        limit: int = 100,
    ) -> list[CalendarExportToken]:
        filters = [
            CalendarExportTokenRow.organization_id == str(organization_id),
            CalendarExportTokenRow.user_id == str(user_id),
        ]
        if not include_revoked:
            filters.append(CalendarExportTokenRow.revoked_at.is_(None))
        result = await self._session.execute(
            select(CalendarExportTokenRow)
            .where(and_(*filters))
            .order_by(desc(CalendarExportTokenRow.created_at))
            .limit(max(1, min(int(limit), 500)))
        )
        return [row_to_calendar_export_token(r) for r in result.scalars().all()]

    async def add(
        self,
        *,
        organization_id: UUID | str,
        user_id: UUID | str,
        token_hash: str,
        scope: CalendarScope,
        target_id: str | None,
        filter_json: dict[str, Any] | None,
        expires_at: datetime,
        audit_correlation_id: str = "",
    ) -> CalendarExportToken:
        now = _now()
        row = CalendarExportTokenRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=str(user_id),
            token_hash=token_hash,
            scope=scope.value,
            target_id=target_id,
            filter_json=_serialize_filter(filter_json),
            expires_at=expires_at,
            revoked_at=None,
            last_used_at=None,
            use_count=0,
            audit_correlation_id=audit_correlation_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_calendar_export_token(row)

    async def revoke(
        self, organization_id: UUID | str, token_id: UUID | str, *, user_id: UUID | str
    ) -> CalendarExportToken | None:
        result = await self._session.execute(
            select(CalendarExportTokenRow).where(
                and_(
                    CalendarExportTokenRow.id == str(token_id),
                    CalendarExportTokenRow.organization_id == str(organization_id),
                    CalendarExportTokenRow.user_id == str(user_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if row.revoked_at is None:
            row.revoked_at = _now()
            row.updated_at = _now()
            await self._session.flush()
        return row_to_calendar_export_token(row)

    async def record_use(
        self, organization_id: UUID | str, token_id: UUID | str
    ) -> CalendarExportToken | None:
        result = await self._session.execute(
            select(CalendarExportTokenRow).where(
                and_(
                    CalendarExportTokenRow.id == str(token_id),
                    CalendarExportTokenRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.last_used_at = _now()
        row.use_count = int(row.use_count or 0) + 1
        row.updated_at = _now()
        await self._session.flush()
        return row_to_calendar_export_token(row)


# ---------------------------------------------------------------------------
# Audit repository
# ---------------------------------------------------------------------------


class CalendarExportAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        user_id: str | None,
        token_id: str | None,
        scope: CalendarScope,
        event_id: str | None,
        event_count: int,
        result: CalendarExportResult,
        ip_address: str,
        user_agent: str,
        request_id: str,
    ) -> CalendarExportAudit:
        row = CalendarExportAuditRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=user_id,
            token_id=token_id,
            scope=scope.value,
            event_id=event_id,
            event_count=int(event_count),
            result=result.value,
            ip_address=ip_address[:64],
            user_agent=user_agent[:256],
            request_id=request_id[:64],
            created_at=_now(),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_calendar_export_audit(row)

    async def list_for_user(
        self,
        organization_id: UUID | str,
        user_id: UUID | str,
        *,
        limit: int = 50,
    ) -> list[CalendarExportAudit]:
        result = await self._session.execute(
            select(CalendarExportAuditRow)
            .where(
                and_(
                    CalendarExportAuditRow.organization_id == str(organization_id),
                    CalendarExportAuditRow.user_id == str(user_id),
                )
            )
            .order_by(desc(CalendarExportAuditRow.created_at))
            .limit(max(1, min(int(limit), 500)))
        )
        return [row_to_calendar_export_audit(r) for r in result.scalars().all()]

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        result: CalendarExportResult | None = None,
        limit: int = 50,
    ) -> list[CalendarExportAudit]:
        filters = [CalendarExportAuditRow.organization_id == str(organization_id)]
        if result is not None:
            filters.append(CalendarExportAuditRow.result == result.value)
        total = await self._session.execute(
            select(func.count(CalendarExportAuditRow.id)).where(and_(*filters))
        )
        _ = total.scalar_one()  # kept for parity with the metrics export list path
        rows = (
            await self._session.execute(
                select(CalendarExportAuditRow)
                .where(and_(*filters))
                .order_by(desc(CalendarExportAuditRow.created_at))
                .limit(max(1, min(int(limit), 500)))
            )
        ).scalars().all()
        return [row_to_calendar_export_audit(r) for r in rows]


__all__ = [
    "CalendarExportAuditRepository",
    "CalendarExportTokenRepository",
]
