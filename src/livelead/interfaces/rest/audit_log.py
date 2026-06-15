"""Admin audit-log API (US-026)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
)
from livelead.domain.audit.model import (
    AuditActor,
    AuditContext,
    AuditEntry,
    AuditTarget,
    action_family as derive_action_family,
)
from livelead.domain.identity import can_access_audit_log
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.request_context import capture_request_context

logger = logging.getLogger("livelead.audit_api")

router = APIRouter(prefix="/admin/audit-logs", tags=["audit-log"])


class AuditEntrySchema(BaseModel):
    id: UUID
    organization_id: UUID
    actor: dict[str, Any]
    action: str
    action_family: str
    target: dict[str, Any]
    outcome: str
    occurred_at: str
    context: dict[str, str]
    metadata: dict[str, Any]
    metadata_redacted: bool


class AuditListSchema(BaseModel):
    items: list[AuditEntrySchema]
    total: int
    limit: int
    offset: int


class AuditFilterOptionsSchema(BaseModel):
    actor_types: list[str]
    outcomes: list[str]
    action_families: list[str]
    target_types: list[str]


def _entry_to_schema(entry: AuditEntry) -> AuditEntrySchema:
    return AuditEntrySchema(
        id=entry.id,
        organization_id=entry.organization_id,
        actor={
            "actor_id": entry.actor.actor_id,
            "actor_type": entry.actor.actor_type.value,
            "role": entry.actor.role,
        },
        action=entry.action.value,
        action_family=entry.action_family,
        target={
            "target_type": entry.target.target_type.value,
            "target_id": entry.target.target_id,
            "display": entry.target.display,
        },
        outcome=entry.outcome.value,
        occurred_at=entry.occurred_at.isoformat(),
        context=entry.context.safe_dict(),
        metadata=entry.metadata,
        metadata_redacted=entry.metadata_redacted,
    )


def require_audit_access(ctx: TenantContext) -> None:
    if not can_access_audit_log(ctx.role):
        raise HTTPException(status_code=403, detail="audit log role required")


def require_admin(ctx: TenantContext) -> None:  # legacy alias used elsewhere
    if not ctx.is_admin():
        raise HTTPException(status_code=403, detail="admin role required")


@router.get("/filters", response_model=AuditFilterOptionsSchema)
async def list_filter_options(
    tenant: TenantContext = Depends(get_tenant_context),
) -> AuditFilterOptionsSchema:
    require_audit_access(tenant)
    return AuditFilterOptionsSchema(
        actor_types=[t.value for t in AuditActorType],
        outcomes=[o.value for o in AuditOutcome],
        action_families=sorted({derive_action_family(a) for a in AuditAction}),
        target_types=[
            "source",
            "cloakbrowser_policy",
            "content_draft",
            "browser_session",
            "browser_confirmation",
            "lead",
            "session",
            "user",
            "membership",
            "invitation",
            "notification",
            "notification_preference",
            "notification_delivery",
            "workflow",
            "system",
        ],
    )


@router.get("", response_model=AuditListSchema)
async def list_audit_entries(
    request: Request,
    actor_id: str | None = Query(default=None, max_length=128),
    actor_type: str | None = Query(default=None, max_length=16),
    action: str | None = Query(default=None, max_length=96),
    action_family: str | None = Query(default=None, max_length=48),
    target_type: str | None = Query(default=None, max_length=48),
    target_id: str | None = Query(default=None, max_length=96),
    outcome: str | None = Query(default=None, max_length=24),
    request_id: str | None = Query(default=None, max_length=64),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AuditListSchema:
    require_audit_access(tenant)
    svc = AuditService(session)
    entries, total = await svc.list_entries(
        tenant.organization_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        action_family=action_family,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        request_id=request_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return AuditListSchema(
        items=[_entry_to_schema(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{entry_id}", response_model=AuditEntrySchema)
async def get_audit_entry(
    entry_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AuditEntrySchema:
    require_audit_access(tenant)
    svc = AuditService(session)
    entry = await svc.get_entry(entry_id, tenant.organization_id)
    if not entry:
        raise HTTPException(status_code=404, detail="audit entry not found")
    await session.commit()
    return _entry_to_schema(entry)


async def record_unauthorized_audit_read(
    session: AsyncSession,
    tenant: TenantContext,
    request: Request,
    *,
    detail: str,
) -> None:
    """Helper for emitting a denied audit entry when a non-admin reads /admin/audit-logs.

    Best-effort — never raises into the original HTTP path.
    """

    try:
        ctx = capture_request_context(request, workflow="admin_audit_read")
        await AuditService(session).emit(
            organization_id=tenant.organization_id,
            actor=make_actor_from_role(tenant.actor_role),
            action=AuditAction.SOURCE_POLICY_DENIED,
            target=AuditTarget(
                target_type="system",
                target_id="admin/audit-logs",
                display="admin/audit-logs",
            ),
            outcome=AuditOutcome.DENIED,
            context=ctx,
            metadata={"reason": detail, "endpoint": str(request.url.path)},
        )
        await session.commit()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("audit_denied_emit_failed err=%s", exc)


def make_actor(tenant: TenantContext) -> AuditActor:
    return make_actor_from_role(tenant.actor_role, actor_id=str(tenant.organization_id))
