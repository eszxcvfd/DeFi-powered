"""Notification persistence repositories (US-029)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.identity import MembershipState, Role
from livelead.domain.notifications import (
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationPreference,
    NotificationState,
    NotificationType,
    SourceRecordType,
    UserNotification,
)
from livelead.infrastructure.db.identity_mappers import row_to_membership
from livelead.infrastructure.db.models import (
    NotificationDeliveryAttemptRow,
    NotificationPreferenceRow,
    OrganizationMembershipRow,
    UserNotificationRow,
    UserRow,
)
from livelead.infrastructure.db.notification_mappers import (
    row_to_delivery_attempt,
    row_to_notification_preference,
    row_to_user_notification,
)


class UserNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        notification_type: NotificationType,
        state: NotificationState,
        source_record_type: SourceRecordType,
        source_record_id: str,
        title: str,
        summary: str,
        deep_link: str,
    ) -> UserNotification:
        now = datetime.now(UTC)
        row = UserNotificationRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=str(user_id),
            notification_type=notification_type.value,
            state=state.value,
            source_record_type=source_record_type.value,
            source_record_id=source_record_id,
            title=title[:300],
            summary=summary[:4000],
            deep_link=deep_link[:1024],
            read_at=None,
            dismissed_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_user_notification(row)

    async def get_for_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        notification_id: UUID,
    ) -> UserNotification | None:
        result = await self._session.execute(
            select(UserNotificationRow).where(
                and_(
                    UserNotificationRow.id == str(notification_id),
                    UserNotificationRow.user_id == str(user_id),
                    UserNotificationRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_user_notification(row) if row else None

    async def list_for_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        state: NotificationState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserNotification]:
        stmt = select(UserNotificationRow).where(
            and_(
                UserNotificationRow.user_id == str(user_id),
                UserNotificationRow.organization_id == str(organization_id),
            )
        )
        if state is not None:
            stmt = stmt.where(UserNotificationRow.state == state.value)
        stmt = stmt.order_by(
            desc(UserNotificationRow.created_at), desc(UserNotificationRow.id)
        ).offset(max(0, int(offset))).limit(max(1, min(int(limit), 200)))
        result = await self._session.execute(stmt)
        return [row_to_user_notification(r) for r in result.scalars().all()]

    async def unread_count(
        self, organization_id: UUID, user_id: UUID
    ) -> int:
        from sqlalchemy import func

        result = await self._session.execute(
            select(func.count(UserNotificationRow.id)).where(
                and_(
                    UserNotificationRow.user_id == str(user_id),
                    UserNotificationRow.organization_id == str(organization_id),
                    UserNotificationRow.state == NotificationState.UNREAD.value,
                )
            )
        )
        return int(result.scalar_one() or 0)

    async def mark_state(
        self,
        organization_id: UUID,
        user_id: UUID,
        notification_id: UUID,
        new_state: NotificationState,
    ) -> UserNotification | None:
        result = await self._session.execute(
            select(UserNotificationRow).where(
                and_(
                    UserNotificationRow.id == str(notification_id),
                    UserNotificationRow.user_id == str(user_id),
                    UserNotificationRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        now = datetime.now(UTC)
        row.state = new_state.value
        if new_state == NotificationState.READ and row.read_at is None:
            row.read_at = now
        if new_state == NotificationState.DISMISSED and row.dismissed_at is None:
            row.dismissed_at = now
        row.updated_at = now
        await self._session.flush()
        return row_to_user_notification(row)


class NotificationPreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(
        self, organization_id: UUID, user_id: UUID
    ) -> list[NotificationPreference]:
        result = await self._session.execute(
            select(NotificationPreferenceRow)
            .where(
                and_(
                    NotificationPreferenceRow.user_id == str(user_id),
                    NotificationPreferenceRow.organization_id == str(organization_id),
                )
            )
            .order_by(NotificationPreferenceRow.notification_type.asc())
        )
        return [row_to_notification_preference(r) for r in result.scalars().all()]

    async def upsert(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        notification_type: NotificationType,
        in_app_enabled: bool,
        email_enabled: bool,
    ) -> NotificationPreference:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(NotificationPreferenceRow).where(
                and_(
                    NotificationPreferenceRow.user_id == str(user_id),
                    NotificationPreferenceRow.organization_id == str(organization_id),
                    NotificationPreferenceRow.notification_type == notification_type.value,
                )
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.in_app_enabled = in_app_enabled
            row.email_enabled = email_enabled
            row.updated_at = now
            await self._session.flush()
            return row_to_notification_preference(row)
        row = NotificationPreferenceRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=str(user_id),
            notification_type=notification_type.value,
            in_app_enabled=in_app_enabled,
            email_enabled=email_enabled,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_notification_preference(row)


class NotificationDeliveryAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        notification_id: UUID,
        notification_type: NotificationType,
        channel: NotificationChannel,
        status: str,
        provider: str,
        provider_message_id: str,
        recipient: str,
        subject: str,
        diagnostics: dict,
    ) -> NotificationDeliveryAttempt:
        now = datetime.now(UTC)
        row = NotificationDeliveryAttemptRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=str(user_id),
            notification_id=str(notification_id),
            notification_type=notification_type.value,
            channel=channel.value,
            status=status,
            provider=provider,
            provider_message_id=provider_message_id[:200],
            recipient=recipient[:320],
            subject=subject[:500],
            diagnostics_json=json.dumps(diagnostics, default=str)[:8000],
            attempted_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_delivery_attempt(row)

    async def list_for_notification(
        self, notification_id: UUID
    ) -> list[NotificationDeliveryAttempt]:
        result = await self._session.execute(
            select(NotificationDeliveryAttemptRow)
            .where(NotificationDeliveryAttemptRow.notification_id == str(notification_id))
            .order_by(desc(NotificationDeliveryAttemptRow.attempted_at))
        )
        return [row_to_delivery_attempt(r) for r in result.scalars().all()]

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        limit: int = 50,
    ) -> list[NotificationDeliveryAttempt]:
        result = await self._session.execute(
            select(NotificationDeliveryAttemptRow)
            .where(
                NotificationDeliveryAttemptRow.organization_id == str(organization_id)
            )
            .order_by(desc(NotificationDeliveryAttemptRow.attempted_at))
            .limit(max(1, min(int(limit), 200)))
        )
        return [row_to_delivery_attempt(r) for r in result.scalars().all()]


class NotificationRecipientResolver:
    """Resolve the active user-and-membership pool for one organization.

    The notification service uses this resolver to find users that
    should receive alerts. The first slice sends reminders to the
    reminder owner, job alerts to the job creator, and event-timing
    alerts to every active member of the organization.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_memberships(
        self, organization_id: UUID
    ) -> list[tuple[UUID, Role]]:
        result = await self._session.execute(
            select(OrganizationMembershipRow)
            .where(
                and_(
                    OrganizationMembershipRow.organization_id == str(organization_id),
                    OrganizationMembershipRow.state == MembershipState.ACTIVE.value,
                )
            )
        )
        out: list[tuple[UUID, Role]] = []
        for row in result.scalars().all():
            membership = row_to_membership(row)
            out.append((membership.user_id, membership.role))
        return out

    async def list_user_emails(
        self, organization_id: UUID
    ) -> dict[UUID, str]:
        result = await self._session.execute(
            select(UserRow.id, UserRow.email)
            .join(
                OrganizationMembershipRow,
                OrganizationMembershipRow.user_id == UserRow.id,
            )
            .where(
                and_(
                    OrganizationMembershipRow.organization_id == str(organization_id),
                    OrganizationMembershipRow.state == MembershipState.ACTIVE.value,
                )
            )
        )
        out: dict[UUID, str] = {}
        for row_id, email in result.all():
            if not row_id or not email:
                continue
            try:
                out[UUID(str(row_id))] = str(email)
            except (TypeError, ValueError):
                continue
        return out


__all__ = [
    "NotificationDeliveryAttemptRepository",
    "NotificationPreferenceRepository",
    "NotificationRecipientResolver",
    "UserNotificationRepository",
]
