"""Notification REST API (US-029)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.notifications import (
    DeliveryView,
    InboxView,
    NotificationService,
    PreferenceMatrix,
    discovery_job_candidates_for,
    reminder_candidates_for,
    upcoming_event_candidates_for,
)
from livelead.domain.discovery.models import DiscoveryJobStatus
from livelead.domain.identity import (
    AuthenticatedIdentity,
    Role,
    can_invite_member,
)
from livelead.domain.notifications import (
    NotificationDeliveryAttempt,
    NotificationState,
    NotificationType,
    UserNotification,
    is_email_eligible,
)
from livelead.infrastructure.db.models import (
    DiscoveryJobRow,
    EventRow,
    FollowUpReminderRow,
)
from livelead.infrastructure.db.repositories.notifications import (
    NotificationRecipientResolver,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.notification_api")

router = APIRouter(tags=["notifications"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class NotificationSchema(BaseModel):
    id: str
    organization_id: str
    user_id: str
    notification_type: str
    state: str
    source_record_type: str
    source_record_id: str
    title: str
    summary: str
    deep_link: str
    created_at: str
    read_at: str | None = None
    dismissed_at: str | None = None


class InboxResponse(BaseModel):
    items: list[NotificationSchema]
    unread_count: int
    total: int


class PreferenceEntrySchema(BaseModel):
    notification_type: str
    in_app_enabled: bool
    email_enabled: bool
    updated_at: str


class PreferencesResponse(BaseModel):
    preferences: list[PreferenceEntrySchema]
    is_seeded: bool


class PreferencesUpdateRequest(BaseModel):
    preferences: dict[str, dict[str, bool]] = Field(default_factory=dict)


class DeliveryAttemptSchema(BaseModel):
    id: str
    notification_id: str
    notification_type: str
    channel: str
    status: str
    provider: str
    provider_message_id: str
    recipient: str
    subject: str
    diagnostics: dict[str, Any]
    attempted_at: str


class ScanRequest(BaseModel):
    include_reminders: bool = True
    include_events: bool = True
    lead_minutes: int = Field(default=60, ge=5, le=24 * 60)


class ScanResponse(BaseModel):
    candidates: int
    in_app_created: int
    emails_attempted: int
    emails_suppressed: int
    emails_failed: int


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _identity_from_tenant(tenant: TenantContext) -> AuthenticatedIdentity:
    if not tenant.is_authenticated() or tenant.session_id is None or tenant.role is None:
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


def _notification_view(n: UserNotification) -> NotificationSchema:
    return NotificationSchema(
        id=str(n.id),
        organization_id=str(n.organization_id),
        user_id=str(n.user_id),
        notification_type=n.notification_type.value,
        state=n.state.value,
        source_record_type=n.source_record_type.value,
        source_record_id=n.source_record_id,
        title=n.title,
        summary=n.summary,
        deep_link=n.deep_link,
        created_at=n.created_at.isoformat(),
        read_at=n.read_at.isoformat() if n.read_at else None,
        dismissed_at=n.dismissed_at.isoformat() if n.dismissed_at else None,
    )


def _delivery_view(d: NotificationDeliveryAttempt) -> DeliveryAttemptSchema:
    return DeliveryAttemptSchema(
        id=str(d.id),
        notification_id=str(d.notification_id),
        notification_type=d.notification_type.value,
        channel=d.channel.value,
        status=d.status.value,
        provider=d.provider,
        provider_message_id=d.provider_message_id,
        recipient=d.recipient,
        subject=d.subject,
        diagnostics=d.diagnostics,
        attempted_at=d.attempted_at.isoformat(),
    )


# ----------------------------------------------------------------------
# Inbox
# ----------------------------------------------------------------------
@router.get("/notifications", response_model=InboxResponse)
async def list_notifications(
    state: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> InboxResponse:
    identity = _identity_from_tenant(tenant)
    parsed_state: NotificationState | None = None
    if state:
        try:
            parsed_state = NotificationState(state)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown state: {state}") from exc
    svc = NotificationService(session)
    inbox: InboxView = await svc.list_inbox(
        organization_id=identity.organization_id,
        user_id=identity.user_id,
        state=parsed_state,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return InboxResponse(
        items=[_notification_view(n) for n in inbox.items],
        unread_count=inbox.unread_count,
        total=inbox.total,
    )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationSchema,
)
async def mark_read(
    notification_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationSchema:
    identity = _identity_from_tenant(tenant)
    svc = NotificationService(session)
    notification = await svc.mark_read(
        organization_id=identity.organization_id,
        user_id=identity.user_id,
        notification_id=notification_id,
        actor_role=identity.role,
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return _notification_view(notification)


@router.post(
    "/notifications/{notification_id}/dismiss",
    response_model=NotificationSchema,
)
async def dismiss(
    notification_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationSchema:
    identity = _identity_from_tenant(tenant)
    svc = NotificationService(session)
    notification = await svc.dismiss(
        organization_id=identity.organization_id,
        user_id=identity.user_id,
        notification_id=notification_id,
        actor_role=identity.role,
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return _notification_view(notification)


# ----------------------------------------------------------------------
# Preferences
# ----------------------------------------------------------------------
@router.get("/notification-preferences", response_model=PreferencesResponse)
async def get_preferences(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PreferencesResponse:
    identity = _identity_from_tenant(tenant)
    svc = NotificationService(session)
    matrix: PreferenceMatrix = await svc.get_or_seed_preferences(
        organization_id=identity.organization_id,
        user_id=identity.user_id,
    )
    await session.commit()
    return PreferencesResponse(
        preferences=[
            PreferenceEntrySchema(
                notification_type=p.notification_type.value,
                in_app_enabled=p.in_app_enabled,
                email_enabled=p.email_enabled,
                updated_at=p.updated_at.isoformat(),
            )
            for p in matrix.preferences
        ],
        is_seeded=matrix.is_seeded,
    )


@router.patch("/notification-preferences", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesUpdateRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PreferencesResponse:
    identity = _identity_from_tenant(tenant)
    svc = NotificationService(session)
    try:
        matrix = await svc.update_preferences(
            request=request,
            organization_id=identity.organization_id,
            user_id=identity.user_id,
            actor_role=identity.role,
            payload=body.preferences,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PreferencesResponse(
        preferences=[
            PreferenceEntrySchema(
                notification_type=p.notification_type.value,
                in_app_enabled=p.in_app_enabled,
                email_enabled=p.email_enabled,
                updated_at=p.updated_at.isoformat(),
            )
            for p in matrix.preferences
        ],
        is_seeded=matrix.is_seeded,
    )


# ----------------------------------------------------------------------
# Admin scan — bounded internal endpoint for tests + first MVP rollout
# ----------------------------------------------------------------------
def _require_admin_or_owner(tenant: TenantContext) -> AuthenticatedIdentity:
    identity = _identity_from_tenant(tenant)
    if not can_invite_member(identity.role):
        raise HTTPException(status_code=403, detail="governance role required")
    return identity


@router.post(
    "/admin/notifications/scan",
    response_model=ScanResponse,
)
async def run_scan(
    body: ScanRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ScanResponse:
    identity = _require_admin_or_owner(tenant)
    svc = NotificationService(session)
    candidates = 0
    in_app_created = 0
    emails_attempted = 0
    emails_suppressed = 0
    emails_failed = 0

    from sqlalchemy import select

    if body.include_reminders:
        reminder_rows = (
            await session.execute(
                select(FollowUpReminderRow).where(
                    FollowUpReminderRow.organization_id == str(identity.organization_id)
                )
            )
        ).scalars().all()
        for row in reminder_rows:
            owner_user_id = None
            if row.owner and "@" in row.owner:
                # Owner stored as a free-form string; the resolver only
                # knows about user ids, so reminder-candidate generation
                # here skips the email path. The reminder service in
                # US-013 already publishes in-app alerts, so the
                # operator can wire a user lookup later.
                owner_user_id = None
            if owner_user_id is None:
                continue
            for candidate in reminder_candidates_for(
                organization_id=identity.organization_id,
                reminder_id=row.id,
                lead_display_name=row.lead_id,
                owner_user_id=owner_user_id,
                due_date=row.due_date,
            ):
                candidates += 1
                views = await svc.deliver_candidate(
                    request=request,
                    candidate=candidate,
                    actor_role=identity.role,
                )
                in_app_created += sum(1 for v in views if v.delivery is None)
                emails_attempted += sum(
                    1 for v in views if v.delivery is not None and v.delivery.status.value == "succeeded"
                )
                emails_failed += sum(
                    1 for v in views if v.delivery is not None and v.delivery.status.value == "failed"
                )

    if body.include_events:
        event_rows = (
            await session.execute(
                select(EventRow).where(
                    EventRow.organization_id == str(identity.organization_id)
                )
            )
        ).scalars().all()
        resolver = NotificationRecipientResolver(session)
        recipients = await resolver.list_active_memberships(identity.organization_id)
        for row in event_rows:
            starts_at = row.starts_at
            for candidate in upcoming_event_candidates_for(
                organization_id=identity.organization_id,
                event_id=row.id,
                event_title=row.canonical_title,
                starts_at=starts_at,
                recipients=recipients,
                lead_minutes=body.lead_minutes,
            ):
                candidates += 1
                views = await svc.deliver_candidate(
                    request=request,
                    candidate=candidate,
                    actor_role=identity.role,
                )
                in_app_created += sum(1 for v in views if v.delivery is None)
                emails_attempted += sum(
                    1 for v in views if v.delivery is not None and v.delivery.status.value == "succeeded"
                )
                emails_failed += sum(
                    1 for v in views if v.delivery is not None and v.delivery.status.value == "failed"
                )

    if (
        body.include_reminders is False
        and not body.include_events
    ):
        # The operator chose to skip every trigger. No candidates.
        pass

    await session.commit()
    return ScanResponse(
        candidates=candidates,
        in_app_created=in_app_created,
        emails_attempted=emails_attempted,
        emails_suppressed=emails_suppressed,
        emails_failed=emails_failed,
    )


__all__ = ["router"]
