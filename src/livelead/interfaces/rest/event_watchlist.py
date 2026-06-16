"""Event watchlist REST API (US-030).

Exposes the first user-scoped watchlist slice:

- ``PUT /events/{id}/watchlist`` for current-user watch or reminder
  upsert.
- ``DELETE /events/{id}/watchlist`` for current-user removal.
- ``GET /watchlist/events`` for the current-user watched-events
  list.
- ``GET /events/{id}`` and ``GET /campaigns/{id}/events`` add the
  ``watch`` projection into the response payload so the UI can
  render the toggle without an extra round trip.

The route layer enforces tenant context and current-user identity.
A request without an authenticated session cannot mutate the
watchlist, so dev-header usage is rejected for the watch routes
even when dev headers are allowed for other endpoints.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.event_watchlist import (
    EventWatchlistService,
    WatchlistValidationError,
)
from livelead.domain.event_watchlist.models import (
    EventWatchState,
    WatchlistAction,
    WatchlistReminderStatus,
)
from livelead.domain.identity import AuthenticatedIdentity, Role
from livelead.infrastructure.db.repositories.events import EventRepository
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.event_watchlist_api")

router = APIRouter(tags=["event-watchlist"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class WatchStateSchema(BaseModel):
    event_id: str
    is_watched: bool
    watchlist_entry_id: str | None = None
    reminder_at: str | None = None
    reminder_status: str
    reminder_note: str = ""
    last_action_at: str | None = None
    reminder_eligible: bool = False

    @classmethod
    def from_state(cls, state: EventWatchState) -> "WatchStateSchema":
        return cls(
            event_id=str(state.event_id),
            is_watched=state.is_watched,
            watchlist_entry_id=(
                str(state.watchlist_entry_id) if state.watchlist_entry_id else None
            ),
            reminder_at=state.reminder_at,
            reminder_status=state.reminder_status.value,
            reminder_note=state.reminder_note,
            last_action_at=state.last_action_at,
            reminder_eligible=state.reminder_eligible,
        )


class WatchlistUpsertRequest(BaseModel):
    reminder_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp for the reminder or null to clear.",
    )
    reminder_note: str = Field(default="", max_length=500)


class WatchlistHistorySchema(BaseModel):
    id: str
    action: str
    actor_id: str
    actor_role: str
    from_reminder_at: str | None
    to_reminder_at: str | None
    note: str
    created_at: str


class WatchlistEntryResponse(BaseModel):
    entry_id: str
    watch: WatchStateSchema
    history: list[WatchlistHistorySchema] = Field(default_factory=list)


class WatchedEventRowSchema(BaseModel):
    entry_id: str
    event_id: str
    campaign_id: str
    campaign_name: str
    canonical_title: str
    source_url: str
    observed_at: str
    region: str
    starts_at: str | None = None
    reminder_at: str | None = None
    reminder_status: str
    reminder_note: str
    last_action_at: str | None = None


class WatchedEventListResponse(BaseModel):
    items: list[WatchedEventRowSchema]
    total: int


class EventDetailWatchExtension(BaseModel):
    watch: WatchStateSchema


# ----------------------------------------------------------------------
# Identity helpers
# ----------------------------------------------------------------------
def _identity_from_tenant(tenant: TenantContext) -> AuthenticatedIdentity:
    if (
        not tenant.is_authenticated()
        or not tenant.actor_id
        or tenant.session_id is None
        or tenant.role is None
    ):
        raise HTTPException(status_code=401, detail="authentication required")
    return AuthenticatedIdentity(
        user_id=UUID(tenant.actor_id),
        email=tenant.email,
        display_name=tenant.display_name,
        organization_id=tenant.organization_id,
        role=tenant.role,
        session_id=tenant.session_id,
        expires_at=None,  # type: ignore[arg-type]
    )


def _request_id(request: Request) -> str:
    return (
        request.headers.get("x-request-id")
        or request.headers.get("X-Request-ID")
        or ""
    )


def _serialize_history(history) -> list[WatchlistHistorySchema]:
    return [
        WatchlistHistorySchema(
            id=str(h.id),
            action=h.action.value if isinstance(h.action, WatchlistAction) else str(h.action),
            actor_id=h.actor_id,
            actor_role=h.actor_role,
            from_reminder_at=h.from_reminder_at,
            to_reminder_at=h.to_reminder_at,
            note=h.note,
            created_at=h.created_at.isoformat().replace("+00:00", "Z"),
        )
        for h in history
    ]


def _serialize_watched_row(item) -> WatchedEventRowSchema:
    return WatchedEventRowSchema(
        entry_id=str(item.entry_id),
        event_id=str(item.event_id),
        campaign_id=str(item.campaign_id),
        campaign_name=item.campaign_name,
        canonical_title=item.canonical_title,
        source_url=item.source_url,
        observed_at=item.observed_at.isoformat().replace("+00:00", "Z"),
        region=item.region or "",
        starts_at=item.starts_at.isoformat().replace("+00:00", "Z") if item.starts_at else None,
        reminder_at=(
            item.reminder_at.isoformat().replace("+00:00", "Z")
            if item.reminder_at
            else None
        ),
        reminder_status=item.reminder_status.value,
        reminder_note=item.reminder_note,
        last_action_at=(
            item.last_action_at.isoformat().replace("+00:00", "Z")
            if item.last_action_at
            else None
        ),
    )


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@router.put(
    "/events/{event_id}/watchlist",
    response_model=WatchlistEntryResponse,
)
async def upsert_watchlist_entry(
    event_id: UUID,
    body: WatchlistUpsertRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistEntryResponse:
    identity = _identity_from_tenant(tenant)
    events = EventRepository(session)
    if not await events.get(event_id, identity.organization_id):
        raise HTTPException(status_code=404, detail="event not found")
    svc = EventWatchlistService(session)
    try:
        result = await svc.upsert(
            organization_id=identity.organization_id,
            user_id=identity.user_id,
            actor_id=str(identity.user_id),
            actor_role=identity.role.value,
            event_id=event_id,
            reminder_at_raw=body.reminder_at,
            reminder_note=body.reminder_note,
            request_id=_request_id(request),
        )
    except WatchlistValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    history = await svc._history.list_for_event(  # noqa: SLF001 - intentional service peek
        identity.organization_id,
        identity.user_id,
        event_id,
        limit=5,
    )
    await session.commit()
    return WatchlistEntryResponse(
        entry_id=str(result.entry.id),
        watch=WatchStateSchema.from_state(
            await svc.get_state(identity.organization_id, identity.user_id, event_id)
        ),
        history=_serialize_history(history),
    )


@router.delete(
    "/events/{event_id}/watchlist",
    response_model=WatchlistEntryResponse,
)
async def remove_watchlist_entry(
    event_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistEntryResponse:
    identity = _identity_from_tenant(tenant)
    svc = EventWatchlistService(session)
    await svc.remove(
        organization_id=identity.organization_id,
        user_id=identity.user_id,
        actor_id=str(identity.user_id),
        actor_role=identity.role.value,
        event_id=event_id,
        request_id=_request_id(request),
    )
    history = await svc._history.list_for_event(  # noqa: SLF001 - intentional service peek
        identity.organization_id,
        identity.user_id,
        event_id,
        limit=5,
    )
    await session.commit()
    return WatchlistEntryResponse(
        entry_id="",
        watch=WatchStateSchema.from_state(
            await svc.get_state(identity.organization_id, identity.user_id, event_id)
        ),
        history=_serialize_history(history),
    )


@router.get(
    "/watchlist/events",
    response_model=WatchedEventListResponse,
)
async def list_watched_events(
    has_reminder: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WatchedEventListResponse:
    identity = _identity_from_tenant(tenant)
    svc = EventWatchlistService(session)
    items = await svc.list_for_user(
        identity.organization_id,
        identity.user_id,
        has_reminder=has_reminder,
        limit=limit,
    )
    await session.commit()
    return WatchedEventListResponse(
        items=[_serialize_watched_row(item) for item in items],
        total=len(items),
    )


__all__ = [
    "EventDetailWatchExtension",
    "WatchStateSchema",
    "WatchedEventListResponse",
    "WatchedEventRowSchema",
    "WatchlistEntryResponse",
    "WatchlistHistorySchema",
    "WatchlistReminderStatus",
    "WatchlistUpsertRequest",
    "router",
]
