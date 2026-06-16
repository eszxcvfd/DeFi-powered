"""Event manual-override REST API (US-031).

Exposes the first governed canonical-event edit slice:

- ``PATCH /events/{id}`` for one or more allowed-field updates.
- ``POST /events/{id}/overrides/{field}/clear`` for clearing one
  manual override and restoring the source-backed baseline.
- ``GET /events/{id}/history`` for the append-only change history.
- ``GET /events/{id}`` carries an ``overrides`` projection that
  shows which effective canonical fields come from a manual
  override versus the source-backed value.

The route layer enforces tenant context, current-user
authorization, and the editable-field allowlist. Denied edits and
clear attempts emit an audit row so governance can review them.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.event_overrides import (
    EventOverrideDenied,
    EventOverrideError,
    EventOverrideService,
)
from livelead.domain.event_overrides.models import (
    ALLOWED_OVERRIDE_FIELDS,
    EventChangeHistoryEntry,
    EventManualOverride,
    FieldProvenance,
    format_override_value,
)
from livelead.domain.identity import (
    AuthenticatedIdentity,
    Role,
    can_edit_canonical_event,
    parse_role,
)
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.event_overrides_api")

router = APIRouter(tags=["event-overrides"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class EventOverrideEntrySchema(BaseModel):
    field: str
    override_value: Any = None
    source_value: Any = None
    value_kind: str
    note: str = ""
    actor_id: str = ""
    actor_role: str = ""
    updated_at: str | None = None

    @classmethod
    def from_domain(cls, override: EventManualOverride) -> "EventOverrideEntrySchema":
        return cls(
            field=override.field,
            override_value=format_override_value(override.field, override.override_value),
            source_value=format_override_value(override.field, override.source_backed_value),
            value_kind=override.value_kind.value,
            note=override.note,
            actor_id=override.actor_id,
            actor_role=override.actor_role,
            updated_at=override.updated_at.isoformat().replace("+00:00", "Z"),
        )


class FieldProvenanceSchema(BaseModel):
    field: str
    effective_value: Any = None
    source_value: Any = None
    is_overridden: bool = False
    actor_id: str = ""
    actor_role: str = ""
    updated_at: str | None = None

    @classmethod
    def from_domain(cls, item: FieldProvenance) -> "FieldProvenanceSchema":
        return cls(
            field=item.field,
            effective_value=item.effective_value,
            source_value=item.source_value,
            is_overridden=item.is_overridden,
            actor_id=item.actor_id,
            actor_role=item.actor_role,
            updated_at=item.updated_at,
        )


class EventChangeHistorySchema(BaseModel):
    id: str
    action: str
    field: str
    value_kind: str
    prior_value: Any = None
    new_value: Any = None
    source_value: Any = None
    actor_id: str
    actor_role: str
    reason: str
    created_at: str

    @classmethod
    def from_domain(cls, entry: EventChangeHistoryEntry) -> "EventChangeHistorySchema":
        return cls(
            id=str(entry.id),
            action=entry.action.value,
            field=entry.field,
            value_kind=entry.value_kind.value,
            prior_value=format_override_value(entry.field, entry.prior_value),
            new_value=format_override_value(entry.field, entry.new_value),
            source_value=format_override_value(entry.field, entry.source_backed_value),
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            reason=entry.reason,
            created_at=entry.created_at.isoformat().replace("+00:00", "Z"),
        )


class EventPatchRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=500)


class EventOverrideUpdateResponse(BaseModel):
    event_id: str
    applied_fields: list[str]
    skipped_fields: list[dict[str, str]] = Field(default_factory=list)
    overrides: list[EventOverrideEntrySchema] = Field(default_factory=list)
    history: list[EventChangeHistorySchema] = Field(default_factory=list)


class EventOverrideClearRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class EventOverrideClearResponse(BaseModel):
    event_id: str
    field: str
    restored_value: Any = None
    history: list[EventChangeHistorySchema] = Field(default_factory=list)


class EventChangeHistoryResponse(BaseModel):
    event_id: str
    history: list[EventChangeHistorySchema]
    total: int


class EventOverridesResponse(BaseModel):
    event_id: str
    fields_allowed: list[str]
    overrides: list[EventOverrideEntrySchema]
    provenance: list[FieldProvenanceSchema]


# ----------------------------------------------------------------------
# Identity helper
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


def _role_or_default(tenant: TenantContext) -> Role:
    role = parse_role(tenant.actor_role)
    if role is None:
        raise HTTPException(status_code=403, detail="role cannot edit canonical events")
    return role


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@router.patch(
    "/events/{event_id}",
    response_model=EventOverrideUpdateResponse,
)
async def patch_event(
    event_id: UUID,
    body: EventPatchRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> EventOverrideUpdateResponse:
    identity = _identity_from_tenant(tenant)
    role = _role_or_default(tenant)
    if not can_edit_canonical_event(role):
        raise HTTPException(status_code=403, detail="role cannot edit canonical events")
    svc = EventOverrideService(session)
    try:
        result = await svc.update_event_fields(
            organization_id=identity.organization_id,
            actor_id=str(identity.user_id),
            actor_role=role,
            event_id=event_id,
            updates=body.updates,
            request_id=_request_id(request),
            reason=body.reason,
        )
    except EventOverrideDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EventOverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return EventOverrideUpdateResponse(
        event_id=str(result.event_id),
        applied_fields=result.applied_fields,
        skipped_fields=[{"field": f, "reason": r} for f, r in result.skipped_fields],
        overrides=[EventOverrideEntrySchema.from_domain(o) for o in result.overrides],
        history=[EventChangeHistorySchema.from_domain(h) for h in result.history],
    )


@router.post(
    "/events/{event_id}/overrides/{field}/clear",
    response_model=EventOverrideClearResponse,
)
async def clear_event_override(
    event_id: UUID,
    field: str,
    body: EventOverrideClearRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> EventOverrideClearResponse:
    identity = _identity_from_tenant(tenant)
    role = _role_or_default(tenant)
    if not can_edit_canonical_event(role):
        raise HTTPException(status_code=403, detail="role cannot clear overrides")
    if field not in ALLOWED_OVERRIDE_FIELDS:
        raise HTTPException(status_code=400, detail=f"unsupported field: {field}")
    svc = EventOverrideService(session)
    try:
        result = await svc.clear_override(
            organization_id=identity.organization_id,
            actor_id=str(identity.user_id),
            actor_role=role,
            event_id=event_id,
            field=field,
            request_id=_request_id(request),
            reason=body.reason,
        )
    except EventOverrideDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EventOverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return EventOverrideClearResponse(
        event_id=str(result.event_id),
        field=result.field,
        restored_value=result.restored_value,
        history=[EventChangeHistorySchema.from_domain(h) for h in result.history],
    )


@router.get(
    "/events/{event_id}/overrides",
    response_model=EventOverridesResponse,
)
async def list_event_overrides(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> EventOverridesResponse:
    identity = _identity_from_tenant(tenant)
    svc = EventOverrideService(session)
    overrides = await svc.list_overrides(identity.organization_id, event_id)
    provenance = await svc.project_field_provenance(identity.organization_id, event_id)
    await session.commit()
    return EventOverridesResponse(
        event_id=str(event_id),
        fields_allowed=sorted(ALLOWED_OVERRIDE_FIELDS),
        overrides=[EventOverrideEntrySchema.from_domain(o) for o in overrides],
        provenance=[FieldProvenanceSchema.from_domain(p) for p in provenance],
    )


@router.get(
    "/events/{event_id}/history",
    response_model=EventChangeHistoryResponse,
)
async def list_event_history(
    event_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> EventChangeHistoryResponse:
    identity = _identity_from_tenant(tenant)
    svc = EventOverrideService(session)
    history = await svc.list_history(identity.organization_id, event_id, limit=limit)
    await session.commit()
    return EventChangeHistoryResponse(
        event_id=str(event_id),
        history=[EventChangeHistorySchema.from_domain(h) for h in history],
        total=len(history),
    )


__all__ = [
    "EventChangeHistoryResponse",
    "EventChangeHistorySchema",
    "EventOverrideClearRequest",
    "EventOverrideClearResponse",
    "EventOverrideEntrySchema",
    "EventOverrideUpdateResponse",
    "EventOverridesResponse",
    "FieldProvenanceSchema",
    "router",
]
