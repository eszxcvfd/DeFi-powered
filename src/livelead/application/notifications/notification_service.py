"""Notification application service (US-029).

Owns the in-app inbox, the per-user preferences, and the email
delivery attempts. Trigger code (reminder queue, discovery-job
transitions, event timing) calls the service through one of the
candidate-producing helpers. The service applies preferences,
persists the inbox row, attempts the email, and records audit
evidence.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import (
    AuditActor,
    AuditContext,
    AuditTarget,
)
from livelead.domain.identity import Role
from livelead.domain.notifications import (
    DEFAULT_EMAIL_PREFERENCES,
    DEFAULT_IN_APP_PREFERENCES,
    DeliveryStatus,
    NotificationCandidate,
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationPreference,
    NotificationState,
    NotificationType,
    SourceRecordType,
    UserNotification,
    default_preference_matrix,
    is_email_eligible,
    normalize_preference_payload,
    should_attempt_email,
    should_create_in_app,
    summarize_candidate,
    upcoming_event_window,
)
from livelead.infrastructure.db.repositories.notifications import (
    NotificationDeliveryAttemptRepository,
    NotificationPreferenceRepository,
    NotificationRecipientResolver,
    UserNotificationRepository,
)
from livelead.infrastructure.notifications.email_provider import (
    EmailRequest,
    InMemoryEmailProvider,
    NotificationProviderAdapter,
)
from livelead.interfaces.rest.request_context import capture_request_context

logger = logging.getLogger("livelead.notifications")


@dataclass(frozen=True, slots=True)
class InboxView:
    items: list[UserNotification]
    unread_count: int
    total: int


@dataclass(frozen=True, slots=True)
class PreferenceMatrix:
    preferences: list[NotificationPreference]
    is_seeded: bool


@dataclass(frozen=True, slots=True)
class DeliveryView:
    notification: UserNotification
    delivery: NotificationDeliveryAttempt
    suppressed_reason: str | None = None


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        email_provider: NotificationProviderAdapter | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._notifications = UserNotificationRepository(session)
        self._preferences = NotificationPreferenceRepository(session)
        self._deliveries = NotificationDeliveryAttemptRepository(session)
        self._recipients = NotificationRecipientResolver(session)
        self._audit = audit_service or AuditService(session)
        self._email = email_provider or InMemoryEmailProvider()

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def email_provider(self) -> NotificationProviderAdapter:
        return self._email

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------
    async def list_inbox(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        state: NotificationState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InboxView:
        items = await self._notifications.list_for_user(
            organization_id, user_id, state=state, limit=limit, offset=offset
        )
        unread = await self._notifications.unread_count(organization_id, user_id)
        return InboxView(items=items, unread_count=unread, total=len(items))

    async def mark_read(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        notification_id: UUID,
        actor_role: Role,
    ) -> UserNotification | None:
        notification = await self._notifications.mark_state(
            organization_id, user_id, notification_id, NotificationState.READ
        )
        if notification is None:
            return None
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role.value, actor_id=str(user_id)),
            action=AuditAction.NOTIFICATION_DELIVERED,
            target=AuditTarget(
                target_type=AuditTargetType.NOTIFICATION,
                target_id=str(notification.id),
                display=notification.title,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=AuditContext(workflow="notification.read"),
            metadata={
                "notification_id": str(notification.id),
                "new_state": NotificationState.READ.value,
                "notification_type": notification.notification_type.value,
            },
        )
        await self._session.commit()
        return notification

    async def dismiss(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        notification_id: UUID,
        actor_role: Role,
    ) -> UserNotification | None:
        notification = await self._notifications.mark_state(
            organization_id, user_id, notification_id, NotificationState.DISMISSED
        )
        if notification is None:
            return None
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role.value, actor_id=str(user_id)),
            action=AuditAction.NOTIFICATION_DELIVERED,
            target=AuditTarget(
                target_type=AuditTargetType.NOTIFICATION,
                target_id=str(notification.id),
                display=notification.title,
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=AuditContext(workflow="notification.dismiss"),
            metadata={
                "notification_id": str(notification.id),
                "new_state": NotificationState.DISMISSED.value,
                "notification_type": notification.notification_type.value,
            },
        )
        await self._session.commit()
        return notification

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    async def get_or_seed_preferences(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> PreferenceMatrix:
        existing = await self._preferences.list_for_user(organization_id, user_id)
        if existing:
            return PreferenceMatrix(preferences=existing, is_seeded=False)
        seeded: list[NotificationPreference] = []
        for n_type in NotificationType:
            pref = await self._preferences.upsert(
                organization_id=organization_id,
                user_id=user_id,
                notification_type=n_type,
                in_app_enabled=DEFAULT_IN_APP_PREFERENCES.get(n_type, True),
                email_enabled=DEFAULT_EMAIL_PREFERENCES.get(n_type, False),
            )
            seeded.append(pref)
        await self._session.commit()
        return PreferenceMatrix(preferences=seeded, is_seeded=True)

    async def update_preferences(
        self,
        *,
        request: Request | None,
        organization_id: UUID,
        user_id: UUID,
        actor_role: Role,
        payload: dict[str, dict[str, bool]],
    ) -> PreferenceMatrix:
        try:
            typed = normalize_preference_payload(payload)
        except ValueError:
            raise
        updated: list[NotificationPreference] = []
        for n_type, channels in typed.items():
            current = await self._preferences.list_for_user(organization_id, user_id)
            current_for_type = next(
                (p for p in current if p.notification_type == n_type), None
            )
            in_app_value = channels.get(
                NotificationChannel.IN_APP,
                current_for_type.in_app_enabled if current_for_type else True,
            )
            email_value = channels.get(
                NotificationChannel.EMAIL,
                current_for_type.email_enabled if current_for_type else False,
            )
            pref = await self._preferences.upsert(
                organization_id=organization_id,
                user_id=user_id,
                notification_type=n_type,
                in_app_enabled=in_app_value,
                email_enabled=email_value,
            )
            updated.append(pref)
        ctx = capture_request_context(request, workflow="notification.preferences") if request else AuditContext(workflow="notification.preferences")
        try:
            await self._audit.emit(
                organization_id=organization_id,
                actor=make_actor_from_role(actor_role.value, actor_id=str(user_id)),
                action=AuditAction.NOTIFICATION_PREFERENCE_CHANGED,
                target=AuditTarget(
                    target_type=AuditTargetType.NOTIFICATION_PREFERENCE,
                    target_id=str(user_id),
                    display=f"user:{user_id}",
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=ctx,
                metadata={
                    "user_id": str(user_id),
                    "updated_types": [n.value for n in typed.keys()],
                    "preference_payload": _redact_preference_payload(payload),
                },
            )
            await self._session.commit()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("notification_preference_audit_failed err=%s", exc)
        matrix = await self.get_or_seed_preferences(
            organization_id=organization_id, user_id=user_id
        )
        return matrix

    # ------------------------------------------------------------------
    # Trigger helpers
    # ------------------------------------------------------------------
    async def deliver_candidate(
        self,
        *,
        request: Request | None,
        candidate: NotificationCandidate,
        actor_role: Role | None = None,
        existing_notification_id: UUID | None = None,
    ) -> list[DeliveryView]:
        ctx = (
            capture_request_context(request, workflow=f"notification.{candidate.notification_type.value}")
            if request is not None
            else AuditContext(workflow=f"notification.{candidate.notification_type.value}")
        )
        preferences = await self._preferences.list_for_user(
            candidate.organization_id, candidate.user_id
        )
        if not preferences:
            await self._preferences.upsert(
                organization_id=candidate.organization_id,
                user_id=candidate.user_id,
                notification_type=candidate.notification_type,
                in_app_enabled=DEFAULT_IN_APP_PREFERENCES.get(candidate.notification_type, True),
                email_enabled=DEFAULT_EMAIL_PREFERENCES.get(candidate.notification_type, False),
            )
            preferences = await self._preferences.list_for_user(
                candidate.organization_id, candidate.user_id
            )

        views: list[DeliveryView] = []
        notification: UserNotification | None = None

        if not should_create_in_app(candidate.notification_type, preferences):
            await self._audit.emit(
                organization_id=candidate.organization_id,
                actor=AuditActor(
                    actor_id=str(candidate.user_id),
                    actor_type=AuditActorType.HUMAN,
                    role=(actor_role.value if actor_role else "system"),
                ),
                action=AuditAction.NOTIFICATION_SUPPRESSED,
                target=AuditTarget(
                    target_type=AuditTargetType.NOTIFICATION,
                    target_id=f"{candidate.source_record_type.value}/{candidate.source_record_id}",
                    display=candidate.title,
                ),
                outcome=AuditOutcome.DENIED,
                context=ctx,
                metadata={
                    "reason": "in_app_disabled",
                    "notification_type": candidate.notification_type.value,
                    "user_id": str(candidate.user_id),
                },
            )
        else:
            notification = await self._notifications.add(
                organization_id=candidate.organization_id,
                user_id=candidate.user_id,
                notification_type=candidate.notification_type,
                state=NotificationState.UNREAD,
                source_record_type=candidate.source_record_type,
                source_record_id=candidate.source_record_id,
                title=candidate.title,
                summary=candidate.summary,
                deep_link=candidate.deep_link,
            )
            await self._audit.emit(
                organization_id=candidate.organization_id,
                actor=AuditActor(
                    actor_id=str(candidate.user_id),
                    actor_type=AuditActorType.HUMAN,
                    role=(actor_role.value if actor_role else "system"),
                ),
                action=AuditAction.NOTIFICATION_DELIVERED,
                target=AuditTarget(
                    target_type=AuditTargetType.NOTIFICATION,
                    target_id=str(notification.id),
                    display=notification.title,
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=ctx,
                metadata={
                    "channel": NotificationChannel.IN_APP.value,
                    "notification_id": str(notification.id),
                    "notification_type": notification.notification_type.value,
                    "user_id": str(candidate.user_id),
                },
            )
            views.append(DeliveryView(notification=notification, delivery=None))  # type: ignore[arg-type]

        if should_attempt_email(candidate.notification_type, preferences):
            email_view = await self._attempt_email(
                ctx=ctx,
                candidate=candidate,
                actor_role=actor_role,
                existing_notification_id=(
                    notification.id if notification else existing_notification_id
                ),
            )
            if email_view is not None:
                views.append(email_view)
        elif is_email_eligible(candidate.notification_type):
            await self._audit.emit(
                organization_id=candidate.organization_id,
                actor=AuditActor(
                    actor_id=str(candidate.user_id),
                    actor_type=AuditActorType.HUMAN,
                    role=(actor_role.value if actor_role else "system"),
                ),
                action=AuditAction.NOTIFICATION_SUPPRESSED,
                target=AuditTarget(
                    target_type=AuditTargetType.NOTIFICATION_DELIVERY,
                    target_id=f"{candidate.source_record_type.value}/{candidate.source_record_id}",
                    display=candidate.title,
                ),
                outcome=AuditOutcome.DENIED,
                context=ctx,
                metadata={
                    "reason": "email_disabled",
                    "notification_type": candidate.notification_type.value,
                    "user_id": str(candidate.user_id),
                },
            )
        return views

    async def _attempt_email(
        self,
        *,
        ctx: AuditContext,
        candidate: NotificationCandidate,
        actor_role: Role | None,
        existing_notification_id: UUID | None,
    ) -> DeliveryView | None:
        from uuid import uuid4

        subject, body, deep_link = summarize_candidate(candidate)
        recipient_map = await self._recipients.list_user_emails(candidate.organization_id)
        recipient = recipient_map.get(candidate.user_id, "")
        if not recipient:
            await self._audit.emit(
                organization_id=candidate.organization_id,
                actor=AuditActor(
                    actor_id=str(candidate.user_id),
                    actor_type=AuditActorType.HUMAN,
                    role=(actor_role.value if actor_role else "system"),
                ),
                action=AuditAction.NOTIFICATION_SUPPRESSED,
                target=AuditTarget(
                    target_type=AuditTargetType.NOTIFICATION_DELIVERY,
                    target_id=f"{candidate.source_record_type.value}/{candidate.source_record_id}",
                    display=candidate.title,
                ),
                outcome=AuditOutcome.DENIED,
                context=ctx,
                metadata={
                    "reason": "missing_recipient",
                    "notification_type": candidate.notification_type.value,
                    "user_id": str(candidate.user_id),
                },
            )
            return None

        request = EmailRequest(
            recipient=recipient,
            subject=subject,
            body=body,
            notification_id=f"{candidate.source_record_type.value}/{candidate.source_record_id}",
            notification_type=candidate.notification_type.value,
            deep_link=deep_link,
        )
        result = await self._email.send(request)
        attempt = await self._deliveries.add(
            organization_id=candidate.organization_id,
            user_id=candidate.user_id,
            notification_id=existing_notification_id or uuid4(),
            notification_type=candidate.notification_type,
            channel=NotificationChannel.EMAIL,
            status=(
                DeliveryStatus.SUCCEEDED.value
                if result.success
                else DeliveryStatus.FAILED.value
            ),
            provider=self._email.name,
            provider_message_id=result.provider_message_id,
            recipient=recipient,
            subject=subject,
            diagnostics=_redact_email_diagnostics(result.diagnostics, recipient),
        )
        audit_action = (
            AuditAction.NOTIFICATION_DELIVERED
            if result.success
            else AuditAction.NOTIFICATION_DELIVERY_FAILED
        )
        await self._audit.emit(
            organization_id=candidate.organization_id,
            actor=AuditActor(
                actor_id=str(candidate.user_id),
                actor_type=AuditActorType.HUMAN,
                role=(actor_role.value if actor_role else "system"),
            ),
            action=audit_action,
            target=AuditTarget(
                target_type=AuditTargetType.NOTIFICATION_DELIVERY,
                target_id=str(attempt.id),
                display=candidate.title,
            ),
            outcome=AuditOutcome.SUCCEEDED if result.success else AuditOutcome.FAILED,
            context=ctx,
            metadata={
                "channel": NotificationChannel.EMAIL.value,
                "provider": attempt.provider,
                "provider_message_id": attempt.provider_message_id,
                "notification_type": candidate.notification_type.value,
                "user_id": str(candidate.user_id),
                "diagnostics": _redact_email_diagnostics(result.diagnostics, recipient),
            },
        )
        return DeliveryView(
            notification=UserNotification(
                id=attempt.notification_id,
                organization_id=candidate.organization_id,
                user_id=candidate.user_id,
                notification_type=candidate.notification_type,
                state=NotificationState.UNREAD,
                source_record_type=candidate.source_record_type,
                source_record_id=candidate.source_record_id,
                title=candidate.title,
                summary=candidate.summary,
                deep_link=candidate.deep_link,
                created_at=attempt.attempted_at,
                read_at=None,
                dismissed_at=None,
            ),
            delivery=attempt,
        )


def _redact_email_diagnostics(diagnostics: dict[str, Any], recipient: str) -> dict[str, Any]:
    """Return a diagnostics dict safe to persist and audit.

    Strips the recipient email from the diagnostics payload before
    persistence so a database leak or audit-log reader does not see
    raw recipient addresses. The persisted `recipient` column on the
    delivery attempt table still holds the address because the
    operator needs it for delivery debugging, but the audit and
    diagnostics never store it twice.
    """

    safe: dict[str, Any] = {}
    for key, value in diagnostics.items():
        if key.lower() in {"recipient", "to", "email"}:
            continue
        safe[key] = value
    if recipient:
        safe["recipient_domain"] = recipient.split("@", 1)[-1] if "@" in recipient else "local"
    return safe


def _redact_preference_payload(payload: dict[str, dict[str, bool]]) -> str:
    """Serialize a preference payload for audit metadata."""

    try:
        return json.dumps(payload, default=str, sort_keys=True)
    except (TypeError, ValueError):
        return "{}"


__all__ = [
    "DeliveryView",
    "InboxView",
    "NotificationService",
    "PreferenceMatrix",
    "default_preference_matrix",
    "upcoming_event_window",
]
