"""Row mappers for the event calendar export tables (US-045)."""

from __future__ import annotations

import json
from typing import Any

from livelead.domain.calendar_export.enums import (
    CalendarExportResult,
    CalendarScope,
)
from livelead.domain.calendar_export.models import (
    CalendarExportAudit,
    CalendarExportToken,
)
from livelead.infrastructure.db.models import (
    CalendarExportAuditRow,
    CalendarExportTokenRow,
)


def _scope_from_string(value: str | None) -> CalendarScope:
    if not value:
        return CalendarScope.EVENT
    try:
        return CalendarScope(value)
    except ValueError:
        return CalendarScope.EVENT


def _result_from_string(value: str | None) -> CalendarExportResult:
    if not value:
        return CalendarExportResult.FORBIDDEN
    try:
        return CalendarExportResult(value)
    except ValueError:
        return CalendarExportResult.FORBIDDEN


def _parse_filter_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def row_to_calendar_export_token(
    row: CalendarExportTokenRow,
) -> CalendarExportToken:
    return CalendarExportToken(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        scope=_scope_from_string(row.scope),
        target_id=row.target_id,
        filter_json=_parse_filter_json(row.filter_json),
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
        use_count=int(row.use_count or 0),
        audit_correlation_id=row.audit_correlation_id or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_calendar_export_audit(
    row: CalendarExportAuditRow,
) -> CalendarExportAudit:
    return CalendarExportAudit(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        token_id=row.token_id,
        scope=_scope_from_string(row.scope),
        event_id=row.event_id,
        event_count=int(row.event_count or 0),
        result=_result_from_string(row.result),
        ip_address=row.ip_address or "",
        user_agent=row.user_agent or "",
        request_id=row.request_id or "",
        created_at=row.created_at,
    )


__all__ = [
    "row_to_calendar_export_audit",
    "row_to_calendar_export_token",
]
