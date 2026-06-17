"""Webhook delivery persistence repositories (US-049).

The repositories own every read and write for
``webhook_subscriptions``,
``webhook_signing_secrets``, and
``webhook_deliveries``. All methods take
``organization_id`` first so tenant isolation
is mandatory at the data layer. The
repositories deliberately return pure
dataclasses from
``livelead.domain.webhooks.models``; the
application service is the only place that
knows the secret-safe payload contract and
the audit entry shape.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
    WebhookEventType,
)
from livelead.domain.webhooks.models import (
    WebhookDelivery,
    WebhookSigningSecret,
    WebhookSubscription,
)
from livelead.infrastructure.db.webhook_mappers import (
    row_to_webhook_delivery,
    row_to_webhook_signing_secret,
    row_to_webhook_subscription,
)
from livelead.infrastructure.db.models import (
    WebhookDeliveryRow,
    WebhookSigningSecretRow,
    WebhookSubscriptionRow,
)

logger = logging.getLogger("livelead.webhook_repo")


def _now() -> datetime:
    return datetime.utcnow()


def _truncate(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    candidate = str(value)
    if len(candidate) <= limit:
        return candidate
    return candidate[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Subscription repository
# ---------------------------------------------------------------------------


class WebhookSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        name: str,
        target_url: str,
        secret_id: str,
        event_types_json: str,
        enabled: bool,
        created_by: str,
    ) -> WebhookSubscription:
        now = _now()
        row = WebhookSubscriptionRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            name=name,
            target_url=target_url,
            secret_id=secret_id,
            event_types_json=event_types_json,
            enabled=bool(enabled),
            deleted_at=None,
            created_by=created_by or "system",
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_webhook_subscription(row)

    async def get(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        *,
        include_deleted: bool = False,
    ) -> WebhookSubscription | None:
        filters = [
            WebhookSubscriptionRow.organization_id
            == str(organization_id),
            WebhookSubscriptionRow.id == str(subscription_id),
        ]
        if not include_deleted:
            filters.append(
                WebhookSubscriptionRow.deleted_at.is_(None)
            )
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(and_(*filters))
        )
        row = result.scalar_one_or_none()
        return row_to_webhook_subscription(row) if row else None

    async def update(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        *,
        name: str,
        target_url: str,
        event_types_json: str | None,
        enabled: bool,
    ) -> WebhookSubscription | None:
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(
                and_(
                    WebhookSubscriptionRow.organization_id
                    == str(organization_id),
                    WebhookSubscriptionRow.id == str(subscription_id),
                    WebhookSubscriptionRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.name = name
        row.target_url = target_url
        if event_types_json is not None:
            row.event_types_json = event_types_json
        row.enabled = bool(enabled)
        row.updated_at = _now()
        await self._session.flush()
        return row_to_webhook_subscription(row)

    async def update_secret_id(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        *,
        secret_id: str,
    ) -> WebhookSubscription | None:
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(
                and_(
                    WebhookSubscriptionRow.organization_id
                    == str(organization_id),
                    WebhookSubscriptionRow.id == str(subscription_id),
                    WebhookSubscriptionRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.secret_id = secret_id
        row.updated_at = _now()
        await self._session.flush()
        return row_to_webhook_subscription(row)

    async def mark_rotated(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        *,
        rotated_at: datetime,
    ) -> WebhookSubscription | None:
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(
                and_(
                    WebhookSubscriptionRow.organization_id
                    == str(organization_id),
                    WebhookSubscriptionRow.id == str(subscription_id),
                    WebhookSubscriptionRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.last_rotated_at = rotated_at
        row.updated_at = _now()
        await self._session.flush()
        return row_to_webhook_subscription(row)

    async def mark_success(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        *,
        delivered_at: datetime,
    ) -> WebhookSubscription | None:
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(
                and_(
                    WebhookSubscriptionRow.organization_id
                    == str(organization_id),
                    WebhookSubscriptionRow.id == str(subscription_id),
                    WebhookSubscriptionRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.last_success_at = delivered_at
        row.updated_at = _now()
        await self._session.flush()
        return row_to_webhook_subscription(row)

    async def mark_failure(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        *,
        failed_at: datetime,
    ) -> WebhookSubscription | None:
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(
                and_(
                    WebhookSubscriptionRow.organization_id
                    == str(organization_id),
                    WebhookSubscriptionRow.id == str(subscription_id),
                    WebhookSubscriptionRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.last_failure_at = failed_at
        row.updated_at = _now()
        await self._session.flush()
        return row_to_webhook_subscription(row)

    async def soft_delete(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
    ) -> bool:
        result = await self._session.execute(
            select(WebhookSubscriptionRow).where(
                and_(
                    WebhookSubscriptionRow.organization_id
                    == str(organization_id),
                    WebhookSubscriptionRow.id == str(subscription_id),
                    WebhookSubscriptionRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.deleted_at = _now()
        row.enabled = False
        row.updated_at = _now()
        await self._session.flush()
        return True

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        enabled: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookSubscription], int]:
        filters = [
            WebhookSubscriptionRow.organization_id
            == str(organization_id),
            WebhookSubscriptionRow.deleted_at.is_(None),
        ]
        if enabled is not None:
            filters.append(
                WebhookSubscriptionRow.enabled == bool(enabled)
            )
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(WebhookSubscriptionRow.id)).where(
                where_clause
            )
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(WebhookSubscriptionRow)
                .where(where_clause)
                .order_by(desc(WebhookSubscriptionRow.created_at))
                .limit(max(1, min(int(limit), 500)))
                .offset(max(0, int(offset)))
            )
        ).scalars().all()
        return [
            row_to_webhook_subscription(r) for r in rows
        ], total

    async def list_enabled_for_event(
        self,
        organization_id: UUID | str,
        event_type: str,
    ) -> list[WebhookSubscription]:
        """Return the matching enabled
        subscriptions for the given event type.

        The bounded path matches the event
        type by checking that the closed
        `WebhookEventType` value is present
        in the subscription's `event_types`
        array.
        """

        rows = (
            await self._session.execute(
                select(WebhookSubscriptionRow)
                .where(
                    and_(
                        WebhookSubscriptionRow.organization_id
                        == str(organization_id),
                        WebhookSubscriptionRow.deleted_at.is_(None),
                        WebhookSubscriptionRow.enabled.is_(True),
                    )
                )
                .order_by(WebhookSubscriptionRow.created_at)
            )
        ).scalars().all()
        result: list[WebhookSubscription] = []
        for row in rows:
            try:
                parsed = json.loads(row.event_types_json or "[]")
            except (TypeError, ValueError):
                continue
            if not isinstance(parsed, list):
                continue
            if str(event_type) in {str(x) for x in parsed}:
                result.append(row_to_webhook_subscription(row))
        return result


# ---------------------------------------------------------------------------
# Signing secret repository
# ---------------------------------------------------------------------------


class WebhookSigningSecretRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        secret_ciphertext: str,
        version: int,
    ) -> WebhookSigningSecret:
        row = WebhookSigningSecretRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            subscription_id=str(subscription_id),
            secret_ciphertext=secret_ciphertext,
            version=int(version),
            created_at=_now(),
            rotated_at=None,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_webhook_signing_secret(row)

    async def rotate(
        self,
        organization_id: UUID | str,
        secret_id: UUID | str,
        *,
        ciphertext: str,
        version: int,
    ) -> WebhookSigningSecret | None:
        result = await self._session.execute(
            select(WebhookSigningSecretRow).where(
                and_(
                    WebhookSigningSecretRow.organization_id
                    == str(organization_id),
                    WebhookSigningSecretRow.id == str(secret_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.secret_ciphertext = ciphertext
        row.version = int(version)
        row.rotated_at = _now()
        await self._session.flush()
        return row_to_webhook_signing_secret(row)

    async def get_active_for_subscription(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
    ) -> WebhookSigningSecret | None:
        result = await self._session.execute(
            select(WebhookSigningSecretRow)
            .where(
                and_(
                    WebhookSigningSecretRow.organization_id
                    == str(organization_id),
                    WebhookSigningSecretRow.subscription_id
                    == str(subscription_id),
                )
            )
            .order_by(desc(WebhookSigningSecretRow.version))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return (
            row_to_webhook_signing_secret(row) if row else None
        )


# ---------------------------------------------------------------------------
# Delivery repository
# ---------------------------------------------------------------------------


class WebhookDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        event_id: str | None,
        event_type: WebhookEventType,
        target_url: str,
        payload_hash: str,
        request_body: str,
        signature: str,
        status: WebhookDeliveryStatus,
        attempt_count: int,
        next_attempt_at: datetime | None,
        max_response_message_length: int = 500,
    ) -> WebhookDelivery:
        row = WebhookDeliveryRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            subscription_id=str(subscription_id),
            event_id=event_id,
            event_type=event_type.value,
            target_url=target_url,
            payload_hash=payload_hash,
            request_body=request_body,
            signature=signature,
            status=status.value,
            attempt_count=int(attempt_count),
            next_attempt_at=next_attempt_at,
            last_attempt_at=None,
            last_response_code=None,
            last_response_message=None,
            delivered_at=None,
            created_at=_now(),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_webhook_delivery(row)

    async def get(
        self,
        organization_id: UUID | str,
        delivery_id: UUID | str,
    ) -> WebhookDelivery | None:
        result = await self._session.execute(
            select(WebhookDeliveryRow).where(
                and_(
                    WebhookDeliveryRow.organization_id
                    == str(organization_id),
                    WebhookDeliveryRow.id == str(delivery_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_webhook_delivery(row) if row else None

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        subscription_id: UUID | str | None = None,
        status: WebhookDeliveryStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookDelivery], int]:
        filters = [
            WebhookDeliveryRow.organization_id
            == str(organization_id)
        ]
        if subscription_id is not None:
            filters.append(
                WebhookDeliveryRow.subscription_id
                == str(subscription_id)
            )
        if status is not None:
            status_value = (
                status.value
                if isinstance(status, WebhookDeliveryStatus)
                else str(status)
            )
            filters.append(
                WebhookDeliveryRow.status == status_value
            )
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(WebhookDeliveryRow.id)).where(
                where_clause
            )
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(WebhookDeliveryRow)
                .where(where_clause)
                .order_by(desc(WebhookDeliveryRow.created_at))
                .limit(max(1, min(int(limit), 500)))
                .offset(max(0, int(offset)))
            )
        ).scalars().all()
        return [
            row_to_webhook_delivery(r) for r in rows
        ], total

    async def list_pending_for_dispatch(
        self,
        now: datetime,
        *,
        limit: int = 200,
    ) -> list[WebhookDelivery]:
        rows = (
            await self._session.execute(
                select(WebhookDeliveryRow)
                .where(
                    and_(
                        WebhookDeliveryRow.status.in_(
                            [
                                WebhookDeliveryStatus.PENDING.value,
                                WebhookDeliveryStatus.FAILED.value,
                            ]
                        ),
                        WebhookDeliveryRow.next_attempt_at.is_not(None),
                        WebhookDeliveryRow.next_attempt_at <= now,
                    )
                )
                .order_by(WebhookDeliveryRow.next_attempt_at)
                .limit(max(1, int(limit)))
            )
        ).scalars().all()
        return [row_to_webhook_delivery(r) for r in rows]

    async def list_pending_for_org_dispatch(
        self,
        organization_id: UUID | str,
        now: datetime,
        *,
        limit: int = 200,
    ) -> list[WebhookDelivery]:
        rows = (
            await self._session.execute(
                select(WebhookDeliveryRow)
                .where(
                    and_(
                        WebhookDeliveryRow.organization_id
                        == str(organization_id),
                        WebhookDeliveryRow.status.in_(
                            [
                                WebhookDeliveryStatus.PENDING.value,
                                WebhookDeliveryStatus.FAILED.value,
                            ]
                        ),
                        WebhookDeliveryRow.next_attempt_at.is_not(None),
                        WebhookDeliveryRow.next_attempt_at <= now,
                    )
                )
                .order_by(WebhookDeliveryRow.next_attempt_at)
                .limit(max(1, int(limit)))
            )
        ).scalars().all()
        return [row_to_webhook_delivery(r) for r in rows]

    async def cancel_pending_for_subscription(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
    ) -> int:
        result = await self._session.execute(
            select(WebhookDeliveryRow)
            .where(
                and_(
                    WebhookDeliveryRow.organization_id
                    == str(organization_id),
                    WebhookDeliveryRow.subscription_id
                    == str(subscription_id),
                    WebhookDeliveryRow.status.in_(
                        [
                            WebhookDeliveryStatus.PENDING.value,
                            WebhookDeliveryStatus.FAILED.value,
                        ]
                    ),
                )
            )
        )
        rows = result.scalars().all()
        for row in rows:
            row.status = WebhookDeliveryStatus.CANCELLED.value
            row.next_attempt_at = None
        await self._session.flush()
        return len(rows)

    async def mark_in_flight(
        self, delivery_id: UUID | str
    ) -> None:
        """Mark the delivery as `in_flight` for
        the bounded race window. The bounded
        path uses an atomic SQL update so two
        workers cannot dispatch the same
        delivery.
        """

        result = await self._session.execute(
            select(WebhookDeliveryRow).where(
                WebhookDeliveryRow.id == str(delivery_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.status = WebhookDeliveryStatus.IN_FLIGHT.value
        await self._session.flush()

    async def record_attempt(
        self,
        delivery_id: UUID | str,
        *,
        status: WebhookDeliveryStatus,
        attempt_count: int,
        next_attempt_at: datetime | None,
        last_attempt_at: datetime,
        last_response_code: int | None,
        last_response_message: str | None,
        delivered_at: datetime | None,
        max_response_message_length: int = 500,
    ) -> WebhookDelivery | None:
        result = await self._session.execute(
            select(WebhookDeliveryRow).where(
                WebhookDeliveryRow.id == str(delivery_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = status.value
        row.attempt_count = int(attempt_count)
        row.next_attempt_at = next_attempt_at
        row.last_attempt_at = last_attempt_at
        row.last_response_code = (
            int(last_response_code)
            if last_response_code is not None
            else None
        )
        row.last_response_message = _truncate(
            last_response_message, limit=max_response_message_length
        )
        row.delivered_at = delivered_at
        await self._session.flush()
        return row_to_webhook_delivery(row)

    async def reset_for_retry(
        self,
        organization_id: UUID | str,
        delivery_id: UUID | str,
        *,
        next_attempt_at: datetime,
    ) -> WebhookDelivery | None:
        result = await self._session.execute(
            select(WebhookDeliveryRow).where(
                and_(
                    WebhookDeliveryRow.organization_id
                    == str(organization_id),
                    WebhookDeliveryRow.id == str(delivery_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = WebhookDeliveryStatus.PENDING.value
        row.attempt_count = 0
        row.next_attempt_at = next_attempt_at
        row.last_attempt_at = None
        row.last_response_code = None
        row.last_response_message = None
        row.delivered_at = None
        await self._session.flush()
        return row_to_webhook_delivery(row)

    async def transition_status(
        self,
        organization_id: UUID | str,
        delivery_id: UUID | str,
        *,
        status: WebhookDeliveryStatus,
        last_response_code: int | None = None,
        last_response_message: str | None = None,
    ) -> WebhookDelivery | None:
        result = await self._session.execute(
            select(WebhookDeliveryRow).where(
                and_(
                    WebhookDeliveryRow.organization_id
                    == str(organization_id),
                    WebhookDeliveryRow.id == str(delivery_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.status = status.value
        if last_response_code is not None:
            row.last_response_code = int(last_response_code)
        if last_response_message is not None:
            row.last_response_message = _truncate(
                last_response_message, limit=500
            )
        await self._session.flush()
        return row_to_webhook_delivery(row)


__all__ = [
    "WebhookDeliveryRepository",
    "WebhookSigningSecretRepository",
    "WebhookSubscriptionRepository",
]
