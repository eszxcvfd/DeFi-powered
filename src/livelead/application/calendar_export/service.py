"""Event calendar export application service (US-045).

Owns the bounded calendar export path. The
service is the only place that mutates
`calendar_export_tokens` and
`calendar_export_audits` and emits the
`calendar.*` audit entries; the REST layer
calls it from the request handlers.

The service reuses the `SanitizeAlertPayload`
helper from `US-041` for every audit payload.
The calendar export token TTL is bounded by the
`EnvironmentMode` shipped by `US-040` (max 90
days in `pilot_live`, max 30 days in
`test_like`). The calendar `STATUS` mapping
follows `SPEC.md` `FR-NOR-003`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.calendar_export.formatter import (
    build_calendar,
    classify_time_state,
    filter_label as filter_label_text,
)
from livelead.application.calendar_export.tokens import (
    hash_calendar_token,
    mint_calendar_token_plaintext,
    verify_calendar_token,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.calendar_export.enums import (
    CalendarExportResult,
    CalendarScope,
    CalendarTimeState,
    SUPPORTED_CALENDAR_SCOPES,
)
from livelead.domain.calendar_export.models import (
    CalendarExportAudit,
    CalendarExportFilter,
    CalendarExportToken,
    EventTimeStateView,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.repositories.calendar_export import (
    CalendarExportAuditRepository,
    CalendarExportTokenRepository,
)
from livelead.infrastructure.db.repositories.event_watchlist import (
    EventWatchlistRepository,
)
from livelead.infrastructure.db.repositories.events import EventRepository

logger = logging.getLogger("livelead.calendar_export_service")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CalendarExportError(ValueError):
    """Raised when a bounded calendar export operation is rejected."""


class CalendarExportNotFound(CalendarExportError):
    """Raised when the requested event or token is missing."""


class CalendarExportForbidden(CalendarExportError):
    """Raised when the requester cannot access the requested event."""


class CalendarExportInvalidScope(CalendarExportError):
    """Raised when the requested scope is not in the closed enum."""


class CalendarExportTokenExpired(CalendarExportError):
    """Raised when the token is past its expiry."""


class CalendarExportTokenRevoked(CalendarExportError):
    """Raised when the token has been revoked."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


PILOT_LIVE_TTL_DAYS = 90
TEST_LIKE_TTL_DAYS = 30


def _max_ttl_days(environment_mode: EnvironmentMode | str) -> int:
    try:
        mode = (
            environment_mode
            if isinstance(environment_mode, EnvironmentMode)
            else EnvironmentMode(environment_mode)
        )
    except ValueError:
        mode = EnvironmentMode.TEST_LIKE
    if mode is EnvironmentMode.PILOT_LIVE:
        return PILOT_LIVE_TTL_DAYS
    return TEST_LIKE_TTL_DAYS


def _payload_sanitized(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    cleaned, redacted = sanitize_alert_payload(payload)
    if not isinstance(cleaned, dict):
        return {}, redacted
    return cleaned, redacted


def _safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned, _ = _payload_sanitized(payload)
    return cleaned


def _resolve_scope(value: CalendarScope | str) -> CalendarScope:
    if isinstance(value, CalendarScope):
        if value not in SUPPORTED_CALENDAR_SCOPES:
            raise CalendarExportInvalidScope(
                f"CALENDAR_INVALID_SCOPE:{value.value}"
            )
        return value
    candidate = str(value or "")
    if not candidate:
        raise CalendarExportInvalidScope("CALENDAR_INVALID_SCOPE:empty")
    if candidate not in {x.value for x in SUPPORTED_CALENDAR_SCOPES}:
        raise CalendarExportInvalidScope(
            f"CALENDAR_INVALID_SCOPE:{candidate}"
        )
    return CalendarScope(candidate)


def _normalize_expires_at(
    *,
    requested: datetime | None,
    now: datetime,
    environment_mode: EnvironmentMode | str,
) -> datetime:
    """Bound the requested expiry by the current `EnvironmentMode`.

    A missing or past `requested` is replaced with the
    mode default; an `requested` that exceeds the mode
    bound is clipped to the mode bound. A `paused`
    mode reuses the test-like default.

    The function expects `now` to be a naive UTC
    datetime; `requested` may be naive or aware. The
    return value is a naive UTC datetime so the
    SQLAlchemy row can compare it against the database
    columns without a tzinfo mismatch.
    """

    max_days = _max_ttl_days(environment_mode)
    max_expiry = now + timedelta(days=max_days)
    if requested is None:
        return max_expiry
    if requested.tzinfo is not None:
        requested = requested.astimezone(UTC).replace(tzinfo=None)
    if requested > max_expiry:
        return max_expiry
    if requested <= now:
        return now + timedelta(minutes=5)
    return requested


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CalendarExportService:
    """Application service for the bounded calendar export surface.

    The service is the only place that mints calendar
    export tokens, builds ICS payloads, and writes
    `calendar.*` audit entries. The REST layer
    wraps it in Pydantic schemas; the tokenized ICS
    endpoint resolves the user from the token row,
    not from the session.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        token_repo: CalendarExportTokenRepository | None = None,
        audit_repo: CalendarExportAuditRepository | None = None,
        event_repo: EventRepository | None = None,
        watchlist_repo: EventWatchlistRepository | None = None,
        environment_mode: EnvironmentMode | str = EnvironmentMode.TEST_LIKE,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._tokens = token_repo or CalendarExportTokenRepository(session)
        self._audits = audit_repo or CalendarExportAuditRepository(session)
        self._events = event_repo or EventRepository(session)
        self._watchlist = watchlist_repo or EventWatchlistRepository(session)
        self._environment_mode = environment_mode

    # ------------------------------------------------------------------
    # Token lifecycle
    # ------------------------------------------------------------------

    async def mint_token(
        self,
        *,
        organization_id: UUID | str,
        user_id: UUID | str,
        scope: CalendarScope | str,
        target_id: str | None = None,
        filter_json: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> tuple[CalendarExportToken, str]:
        """Mint a bounded calendar export token.

        Returns the persisted token row and the
        plaintext token. The plaintext is the only
        artifact the caller can share with a calendar
        client; subsequent reads of the same `token_id`
        return the row without the plaintext.
        """

        scope_e = _resolve_scope(scope)
        org = str(organization_id)
        user = str(user_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        bounded_expiry = _normalize_expires_at(
            requested=expires_at,
            now=now,
            environment_mode=self._environment_mode,
        )
        filter_payload: dict[str, Any] | None = None
        if scope_e is CalendarScope.EVENT_FILTER:
            filter_payload = (
                CalendarExportFilter.from_json(filter_json).to_json()
            )
        elif filter_json and scope_e is CalendarScope.EVENT:
            # The single-event scope carries `target_id`
            # only; the filter payload is rejected.
            filter_payload = None
        elif filter_json and scope_e is CalendarScope.WATCHLIST:
            filter_payload = None
        else:
            filter_payload = None

        if scope_e is CalendarScope.EVENT and not target_id:
            raise CalendarExportError(
                "CALENDAR_INVALID_SCOPE:event_target_required"
            )
        if scope_e is CalendarScope.EVENT_FILTER and not (
            filter_payload and any(
                v for v in filter_payload.values() if v
            )
        ):
            raise CalendarExportError(
                "CALENDAR_INVALID_SCOPE:event_filter_payload_required"
            )

        plaintext = mint_calendar_token_plaintext()
        token_hash = hash_calendar_token(plaintext)
        correlation_id = str(uuid4())
        row = await self._tokens.add(
            organization_id=org,
            user_id=user,
            token_hash=token_hash,
            scope=scope_e,
            target_id=target_id,
            filter_json=filter_payload,
            expires_at=bounded_expiry,
            audit_correlation_id=correlation_id,
        )
        await self._audits.add(
            organization_id=org,
            user_id=user,
            token_id=row.id,
            scope=scope_e,
            event_id=target_id if scope_e is CalendarScope.EVENT else None,
            event_count=0,
            result=CalendarExportResult.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(actor_role, actor_id=actor or user or None),
            action=AuditAction.CALENDAR_TOKEN_MINTED,
            target=AuditTarget(
                target_type=AuditTargetType.CALENDAR_EXPORT_TOKEN,
                target_id=row.id,
                display=f"calendar_export_token:{scope_e.value}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="calendar.token.mint",
            ),
            metadata=_safe_metadata(
                {
                    "scope": scope_e.value,
                    "target_id": target_id,
                    "filter_json": filter_payload,
                    "expires_at": bounded_expiry.isoformat(),
                    "max_ttl_days": _max_ttl_days(self._environment_mode),
                    "environment_mode": str(self._environment_mode),
                }
            ),
        )
        return row, plaintext

    async def revoke_token(
        self,
        *,
        organization_id: UUID | str,
        user_id: UUID | str,
        token_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> CalendarExportToken:
        """Revoke a calendar export token. Idempotent.

        The bounded path emits a
        `calendar.token.revoked` audit entry; a
        missing token returns
        `CalendarExportNotFound` so the caller can
        convert the error into a 404 response.
        """

        org = str(organization_id)
        user = str(user_id)
        existing = await self._tokens.get_for_org(org, token_id)
        if existing is None or existing.user_id != user:
            raise CalendarExportNotFound(
                "CALENDAR_TOKEN_NOT_FOUND"
            )
        revoked = await self._tokens.revoke(org, token_id, user_id=user)
        if revoked is None:
            raise CalendarExportNotFound("CALENDAR_TOKEN_NOT_FOUND")
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(actor_role, actor_id=actor or user or None),
            action=AuditAction.CALENDAR_TOKEN_REVOKED,
            target=AuditTarget(
                target_type=AuditTargetType.CALENDAR_EXPORT_TOKEN,
                target_id=revoked.id,
                display=f"calendar_export_token:{revoked.scope.value}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=revoked.audit_correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="calendar.token.revoke",
            ),
            metadata=_safe_metadata(
                {
                    "scope": revoked.scope.value,
                    "target_id": revoked.target_id,
                    "expires_at": revoked.expires_at.isoformat(),
                }
            ),
        )
        return revoked

    async def resolve_token(
        self,
        *,
        organization_id: UUID | str,
        plaintext: str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> tuple[CalendarExportToken, datetime | None]:
        """Resolve a presented token and update the use counter.

        Returns the token row and the bounded expiry as
        a naive UTC datetime. The caller is
        responsible for the result audit entry shape.
        """

        org = str(organization_id)
        token_hash = hash_calendar_token(plaintext)
        row = await self._tokens.get_by_hash(org, token_hash)
        now = datetime.now(UTC).replace(tzinfo=None)
        if row is None:
            await self._audits.add(
                organization_id=org,
                user_id=None,
                token_id=None,
                scope=CalendarScope.EVENT,
                event_id=None,
                event_count=0,
                result=CalendarExportResult.NOT_FOUND,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            raise CalendarExportNotFound("CALENDAR_TOKEN_NOT_FOUND")
        if row.revoked_at is not None:
            await self._audits.add(
                organization_id=org,
                user_id=row.user_id,
                token_id=row.id,
                scope=row.scope,
                event_id=None,
                event_count=0,
                result=CalendarExportResult.REVOKED,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            raise CalendarExportTokenRevoked("CALENDAR_TOKEN_REVOKED")
        if row.expires_at <= now:
            await self._audits.add(
                organization_id=org,
                user_id=row.user_id,
                token_id=row.id,
                scope=row.scope,
                event_id=None,
                event_count=0,
                result=CalendarExportResult.EXPIRED,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            raise CalendarExportTokenExpired("CALENDAR_TOKEN_EXPIRED")
        updated = await self._tokens.record_use(org, row.id)
        if updated is None:
            raise CalendarExportNotFound("CALENDAR_TOKEN_NOT_FOUND")
        return updated, updated.expires_at

    # ------------------------------------------------------------------
    # ICS builders
    # ------------------------------------------------------------------

    async def build_event_ics(
        self,
        *,
        organization_id: UUID | str,
        requester_id: UUID | str,
        event_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> tuple[str, int]:
        """Build a single-event ICS payload.

        Returns the ICS body and the number of events
        serialized (always 1 for this scope). The
        caller is responsible for the response
        `Content-Disposition` and `Content-Type`
        headers.
        """

        org = str(organization_id)
        event = await self._events.get(event_id, org)
        if event is None:
            await self._audits.add(
                organization_id=org,
                user_id=str(requester_id),
                token_id=None,
                scope=CalendarScope.EVENT,
                event_id=str(event_id),
                event_count=0,
                result=CalendarExportResult.NOT_FOUND,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            raise CalendarExportNotFound("EVENT_NOT_FOUND")
        now = datetime.now(UTC).replace(tzinfo=None)
        view = classify_time_state(
            event_id=str(event.id),
            starts_at=event.starts_at,
            ended_at=None,
            now=now,
        )
        title = event.canonical_title
        description = event.description or ""
        source_url = event.source_url
        location = event.organizer or event.region or ""
        body = build_calendar(
            scope_value=CalendarScope.EVENT.value,
            organization_id=org,
            events=[view],
            titles={str(event.id): title},
            descriptions={str(event.id): description},
            source_urls={str(event.id): source_url},
            locations={str(event.id): location},
            dtstamp=now,
        )
        await self._audits.add(
            organization_id=org,
            user_id=str(requester_id),
            token_id=None,
            scope=CalendarScope.EVENT,
            event_id=str(event.id),
            event_count=1,
            result=CalendarExportResult.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(actor_role, actor_id=actor or str(requester_id) or None),
            action=AuditAction.CALENDAR_EVENT_EXPORTED,
            target=AuditTarget(
                target_type=AuditTargetType.EVENT,
                target_id=str(event.id),
                display=event.canonical_title[:64],
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="calendar.event.export",
            ),
            metadata=_safe_metadata(
                {
                    "scope": CalendarScope.EVENT.value,
                    "event_id": str(event.id),
                    "time_state": view.time_state.value,
                    "calendar_status": _calendar_status_for(view.time_state),
                }
            ),
        )
        return body, 1

    async def build_watchlist_ics(
        self,
        *,
        organization_id: UUID | str,
        user_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> tuple[str, int]:
        """Build the current-user watchlist ICS payload."""

        org = str(organization_id)
        items = await self._watchlist.list_for_user(org, user_id, limit=200)
        if not items:
            return _empty_calendar(CalendarScope.WATCHLIST.value, org), 0
        views, titles, descriptions, source_urls, locations = _project_items(
            items, organization_id=org
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        body = build_calendar(
            scope_value=CalendarScope.WATCHLIST.value,
            organization_id=org,
            events=views,
            titles=titles,
            descriptions=descriptions,
            source_urls=source_urls,
            locations=locations,
            dtstamp=now,
        )
        await self._audits.add(
            organization_id=org,
            user_id=str(user_id),
            token_id=None,
            scope=CalendarScope.WATCHLIST,
            event_id=None,
            event_count=len(views),
            result=CalendarExportResult.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(actor_role, actor_id=actor or str(user_id) or None),
            action=AuditAction.CALENDAR_WATCHLIST_EXPORTED,
            target=AuditTarget(
                target_type=AuditTargetType.WORKFLOW,
                target_id=str(user_id),
                display=f"watchlist:{user_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="calendar.watchlist.export",
            ),
            metadata=_safe_metadata(
                {
                    "scope": CalendarScope.WATCHLIST.value,
                    "event_count": len(views),
                }
            ),
        )
        return body, len(views)

    async def build_filter_ics(
        self,
        *,
        organization_id: UUID | str,
        requester_id: UUID | str,
        filter_obj: CalendarExportFilter,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "system",
    ) -> tuple[str, int]:
        """Build the current event-filter ICS payload."""

        org = str(organization_id)
        events = await self._events.list_for_organization(
            org, q=None, limit=200
        )
        if filter_obj.campaign_id:
            events = [
                e for e in events if str(e.campaign_id) == str(filter_obj.campaign_id)
            ]
        if filter_obj.region:
            events = [
                e for e in events if (e.region or "") == filter_obj.region
            ]
        if not events:
            label = filter_label_text(filter_obj)
            return (
                _empty_calendar(
                    CalendarScope.EVENT_FILTER.value, org, filter_label=label
                ),
                0,
            )
        views, titles, descriptions, source_urls, locations = _project_events(
            events
        )
        label = filter_label_text(filter_obj)
        now = datetime.now(UTC).replace(tzinfo=None)
        body = build_calendar(
            scope_value=CalendarScope.EVENT_FILTER.value,
            organization_id=org,
            events=views,
            titles=titles,
            descriptions=descriptions,
            source_urls=source_urls,
            locations=locations,
            dtstamp=now,
            filter_label=label,
        )
        await self._audits.add(
            organization_id=org,
            user_id=str(requester_id),
            token_id=None,
            scope=CalendarScope.EVENT_FILTER,
            event_id=None,
            event_count=len(views),
            result=CalendarExportResult.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(actor_role, actor_id=actor or str(requester_id) or None),
            action=AuditAction.CALENDAR_FILTER_EXPORTED,
            target=AuditTarget(
                target_type=AuditTargetType.WORKFLOW,
                target_id=label or "default",
                display=label or "default",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="calendar.filter.export",
            ),
            metadata=_safe_metadata(
                {
                    "scope": CalendarScope.EVENT_FILTER.value,
                    "event_count": len(views),
                    "label": label,
                    "filter_json": filter_obj.to_json(),
                }
            ),
        )
        return body, len(views)

    async def build_tokenized_ics(
        self,
        *,
        organization_id: UUID | str,
        plaintext: str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> tuple[str, int, CalendarScope]:
        """Resolve a tokenized request and dispatch to the right builder.

        The dispatcher emits a
        `calendar.token.used` audit entry with the
        result of the token resolution and the inner
        export result. The caller is responsible for
        the response `Content-Disposition` and
        `Content-Type` headers.
        """

        org = str(organization_id)
        token, _ = await self.resolve_token(
            organization_id=org,
            plaintext=plaintext,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if token.scope is CalendarScope.EVENT:
            body, count = await self.build_event_ics(
                organization_id=org,
                requester_id=token.user_id,
                event_id=token.target_id or "",
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=str(token.user_id),
                actor_role="system",
            )
        elif token.scope is CalendarScope.WATCHLIST:
            body, count = await self.build_watchlist_ics(
                organization_id=org,
                user_id=token.user_id,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=str(token.user_id),
                actor_role="system",
            )
        else:
            filter_obj = CalendarExportFilter.from_json(token.filter_json)
            body, count = await self.build_filter_ics(
                organization_id=org,
                requester_id=token.user_id,
                filter_obj=filter_obj,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                actor=str(token.user_id),
                actor_role="system",
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role("system", actor_id=str(token.user_id) or None),
            action=AuditAction.CALENDAR_TOKEN_USED,
            target=AuditTarget(
                target_type=AuditTargetType.CALENDAR_EXPORT_TOKEN,
                target_id=token.id,
                display=f"calendar_export_token:{token.scope.value}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=token.audit_correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="calendar.token.use",
            ),
            metadata=_safe_metadata(
                {
                    "scope": token.scope.value,
                    "event_count": count,
                    "use_count": int(token.use_count or 0),
                }
            ),
        )
        return body, count, token.scope

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list_tokens(
        self,
        organization_id: UUID | str,
        user_id: UUID | str,
        *,
        include_revoked: bool = False,
        limit: int = 100,
    ) -> list[CalendarExportToken]:
        return await self._tokens.list_for_user(
            organization_id,
            user_id,
            include_revoked=include_revoked,
            limit=limit,
        )

    async def list_audits(
        self,
        organization_id: UUID | str,
        user_id: UUID | str,
        *,
        limit: int = 50,
    ) -> list[CalendarExportAudit]:
        return await self._audits.list_for_user(
            organization_id, user_id, limit=limit
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_calendar(
    scope_value: str,
    organization_id: str,
    *,
    filter_label: str = "",
) -> str:
    from livelead.application.calendar_export.formatter import format_calendar_name

    name = format_calendar_name(scope_value, filter_label=filter_label)
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//LiveLead//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        f"X-WR-CALNAME:{name}\r\n"
        "X-WR-TIMEZONE:UTC\r\n"
        f"X-LIVELEAD-CALENDAR-ORG:{organization_id}\r\n"
        "END:VCALENDAR\r\n"
    )


def _project_items(items, *, organization_id: str) -> tuple[
    list[EventTimeStateView],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
]:
    views: list[EventTimeStateView] = []
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    source_urls: dict[str, str] = {}
    locations: dict[str, str] = {}
    now = datetime.now(UTC).replace(tzinfo=None)
    for item in items:
        event_id = str(item.event_id)
        views.append(
            classify_time_state(
                event_id=event_id,
                starts_at=getattr(item, "starts_at", None),
                ended_at=None,
                now=now,
            )
        )
        titles[event_id] = item.canonical_title or ""
        descriptions[event_id] = ""
        source_urls[event_id] = item.source_url or ""
        locations[event_id] = item.region or ""
    views.sort(
        key=lambda v: (v.starts_at or datetime.max.replace(tzinfo=None))
    )
    return views, titles, descriptions, source_urls, locations


def _project_events(events) -> tuple[
    list[EventTimeStateView],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
]:
    views: list[EventTimeStateView] = []
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    source_urls: dict[str, str] = {}
    locations: dict[str, str] = {}
    now = datetime.now(UTC).replace(tzinfo=None)
    for event in events:
        event_id = str(event.id)
        views.append(
            classify_time_state(
                event_id=event_id,
                starts_at=event.starts_at,
                ended_at=None,
                now=now,
            )
        )
        titles[event_id] = event.canonical_title or ""
        descriptions[event_id] = event.description or ""
        source_urls[event_id] = event.source_url or ""
        locations[event_id] = event.organizer or event.region or ""
    views.sort(
        key=lambda v: (v.starts_at or datetime.max.replace(tzinfo=None))
    )
    return views, titles, descriptions, source_urls, locations


def _calendar_status_for(state: CalendarTimeState) -> str:
    from livelead.domain.calendar_export.enums import (
        CALENDAR_STATUS_BY_TIME_STATE,
    )

    return CALENDAR_STATUS_BY_TIME_STATE.get(state, "TENTATIVE")


__all__ = [
    "CalendarExportError",
    "CalendarExportForbidden",
    "CalendarExportInvalidScope",
    "CalendarExportNotFound",
    "CalendarExportService",
    "CalendarExportTokenExpired",
    "CalendarExportTokenRevoked",
    "PILOT_LIVE_TTL_DAYS",
    "TEST_LIKE_TTL_DAYS",
]
