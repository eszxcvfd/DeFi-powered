"""Webhook delivery service (US-049).

Owns the bounded governed webhook delivery
path. The service is the only place that
mutates `webhook_subscriptions` and
`webhook_deliveries`, that rotates the
per-subscription signing secret, and that
emits the `webhook.*` audit entries; the
REST layer calls it from the request
handlers.

The service reuses the `SanitizeAlertPayload`
helper from `US-041` for every payload,
delivery, and audit payload. The bounded
window is enforced by the `EnvironmentMode`
shipped by `US-040` (max 24 hours in
`pilot_live`, max 1 hour in `test_like`).
The service consumes the `AlertEvent` rows
from `US-041`, the
`ConnectorAutoDisableEvent` rows from
`US-048`, the `LeadActivity` rows from
`US-012`, and the `DiscoveryJob` rows from
`US-004`.

The service exposes a bounded
`emit_event` path that the orchestrator
from `US-041` / `US-048` / `US-029` calls
when a documented event fires. The service
exposes a bounded `dispatch_pending` path
that the periodic worker tick from
`US-035` calls.
"""

from __future__ import annotations

import json
import logging
import secrets as _py_secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.webhooks.dispatcher import (
    WebhookDispatcher,
    WebhookHttpPost,
)
from livelead.application.webhooks.retry_policy import (
    bounded_window_seconds,
    next_attempt_at,
)
from livelead.application.webhooks.signer import (
    build_request_body,
    compute_payload_hash,
    sign as _sign,
)
from livelead.application.webhooks.target_url import (
    validate_target_url,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.observability.sanitization import sanitize_alert_payload
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
    WebhookEventType,
)
from livelead.domain.webhooks.models import (
    WebhookDelivery,
    WebhookDeliveryThresholds,
    WebhookSigningSecret,
    WebhookSubscription,
)
from livelead.infrastructure.db.repositories.webhooks import (
    WebhookDeliveryRepository,
    WebhookSigningSecretRepository,
    WebhookSubscriptionRepository,
)
from livelead.infrastructure.secrets.vault import SecretVault

logger = logging.getLogger("livelead.webhook_delivery_service")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class WebhookError(ValueError):
    """Raised when a bounded webhook operation
    is rejected."""


class WebhookSubscriptionNotFound(WebhookError):
    """Raised when the subscription is missing
    or out of tenant scope."""


class WebhookDeliveryNotFound(WebhookError):
    """Raised when the delivery is missing or
    out of tenant scope."""


class WebhookInvalidEventType(WebhookError):
    """Raised when the event type is not in
    the closed `WebhookEventType` enum."""


class WebhookInvalidTargetUrl(WebhookError):
    """Raised when the target URL fails the
    bounded validation."""


class WebhookInvalidPayload(WebhookError):
    """Raised when the payload fails the
    `SanitizeAlertPayload` contract."""


class WebhookEnvironmentPaused(WebhookError):
    """Raised when the `EnvironmentMode` is in
    `paused` state and the operation is
    denied."""


class WebhookRetryExhausted(WebhookError):
    """Raised when the bounded `max_attempts`
    is exhausted."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload_sanitized(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    cleaned, redacted = sanitize_alert_payload(payload)
    if not isinstance(cleaned, dict):
        return {}, redacted
    return cleaned, redacted


def _safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned, _ = _payload_sanitized(payload)
    return cleaned


def _truncate(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    candidate = str(value)
    if len(candidate) <= limit:
        return candidate
    return candidate[: limit - 3] + "..."


def _generate_signing_secret() -> str:
    """Generate a cryptographically-random
    signing secret. The bounded path uses
    `secrets.token_urlsafe(48)` to produce a
    64-character URL-safe string with
    384 bits of entropy.
    """

    return _py_secrets.token_urlsafe(48)


def _parse_event_types(
    event_types: list[str] | tuple[str, ...] | str,
) -> tuple[WebhookEventType, ...]:
    """Parse and validate the bounded
    `event_types` payload.
    """

    if isinstance(event_types, str):
        try:
            event_types = json.loads(event_types)
        except (TypeError, ValueError):
            event_types = [event_types]
    if not isinstance(event_types, (list, tuple)):
        raise WebhookInvalidEventType("WEBHOOK_EVENT_TYPE_INVALID")
    parsed: list[WebhookEventType] = []
    for raw in event_types:
        if not isinstance(raw, str):
            raise WebhookInvalidEventType("WEBHOOK_EVENT_TYPE_INVALID")
        try:
            parsed.append(WebhookEventType(raw))
        except ValueError as exc:
            raise WebhookInvalidEventType(
                "WEBHOOK_EVENT_TYPE_INVALID"
            ) from exc
    return tuple(parsed)


def _serialize_event_types(
    event_types: tuple[WebhookEventType, ...] | tuple[str, ...],
) -> str:
    return json.dumps([et.value for et in event_types], separators=(",", ":"))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class WebhookDeliveryService:
    """Application service for the bounded
    governed webhook delivery surface.

    The service is the only place that runs a
    bounded `emit_event` cycle, persists a
    `WebhookDelivery` row, flips
    `WebhookSubscription.enabled`, and emits
    the `webhook.*` audit entries.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        subscription_repo: WebhookSubscriptionRepository | None = None,
        delivery_repo: WebhookDeliveryRepository | None = None,
        secret_repo: WebhookSigningSecretRepository | None = None,
        vault: SecretVault | None = None,
        dispatcher: WebhookDispatcher | None = None,
        thresholds: WebhookDeliveryThresholds | None = None,
        environment_mode: EnvironmentMode | str = EnvironmentMode.TEST_LIKE,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._subscriptions = (
            subscription_repo or WebhookSubscriptionRepository(session)
        )
        self._deliveries = (
            delivery_repo or WebhookDeliveryRepository(session)
        )
        self._secrets = (
            secret_repo or WebhookSigningSecretRepository(session)
        )
        self._vault = vault
        self._dispatcher = dispatcher or WebhookDispatcher()
        self._thresholds = thresholds or WebhookDeliveryThresholds()
        self._environment_mode = environment_mode

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def subscription_repo(self) -> WebhookSubscriptionRepository:
        return self._subscriptions

    @property
    def delivery_repo(self) -> WebhookDeliveryRepository:
        return self._deliveries

    @property
    def secret_repo(self) -> WebhookSigningSecretRepository:
        return self._secrets

    @property
    def thresholds(self) -> WebhookDeliveryThresholds:
        return self._thresholds

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def create_subscription(
        self,
        *,
        organization_id: UUID | str,
        name: str,
        target_url: str,
        event_types: list[str] | tuple[str, ...] | str,
        enabled: bool = True,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> WebhookSubscription:
        """Create a per-workspace webhook
        subscription.

        The bounded path validates the
        `WebhookEventType` enum and the
        `target_url`. The path generates a new
        per-subscription signing secret, stores
        it encrypted via the `US-003`
        `SecretVault`, and emits a
        `webhook.subscription.created` audit
        entry.
        """

        if not self._vault:
            raise WebhookError("WEBHOOK_VAULT_REQUIRED")
        org = str(organization_id)
        bounded_name = (name or "").strip()[: self._thresholds.max_name_length]
        if not bounded_name:
            raise WebhookError("WEBHOOK_SUBSCRIPTION_NAME_REQUIRED")
        ok, reason = validate_target_url(
            target_url, thresholds=self._thresholds
        )
        if not ok:
            raise WebhookInvalidTargetUrl(reason)
        parsed_event_types = _parse_event_types(event_types)
        if len(parsed_event_types) == 0:
            raise WebhookInvalidEventType("WEBHOOK_EVENT_TYPE_INVALID")
        if (
            len(parsed_event_types)
            > self._thresholds.max_event_types_per_subscription
        ):
            raise WebhookInvalidEventType(
                "WEBHOOK_EVENT_TYPE_INVALID_TOO_MANY"
            )
        correlation_id = str(uuid4())
        # Generate the per-subscription signing
        # secret and persist it encrypted via
        # the `US-003` `SecretVault`.
        plaintext_secret = _generate_signing_secret()
        ciphertext = self._vault.encrypt(plaintext_secret)
        # Create the subscription row first so
        # the foreign key from the secret row
        # is satisfied.
        subscription = await self._subscriptions.add(
            organization_id=org,
            name=bounded_name,
            target_url=target_url,
            secret_id="",  # placeholder; updated below
            event_types_json=_serialize_event_types(
                parsed_event_types
            ),
            enabled=bool(enabled),
            created_by=actor or actor_role or "system",
        )
        secret = await self._secrets.add(
            organization_id=org,
            subscription_id=subscription.id,
            secret_ciphertext=ciphertext,
            version=1,
        )
        # Update the subscription with the
        # secret id; bounded path keeps the
        # relationship consistent.
        updated = await self._subscriptions.update_secret_id(
            org, subscription.id, secret_id=secret.id
        )
        if updated is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.WEBHOOK_SUBSCRIPTION_CREATED,
            target=AuditTarget(
                target_type=AuditTargetType.WEBHOOK_SUBSCRIPTION,
                target_id=updated.id,
                display=(
                    f"webhook_subscription:{updated.id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="webhook.subscription.create",
            ),
            metadata=_safe_metadata(
                {
                    "subscription_id": updated.id,
                    "name": updated.name,
                    "target_url": updated.target_url,
                    "event_types": list(updated.event_types),
                    "enabled": bool(updated.enabled),
                }
            ),
        )
        return updated

    async def update_subscription(
        self,
        *,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        name: str | None = None,
        target_url: str | None = None,
        event_types: list[str] | tuple[str, ...] | str | None = None,
        enabled: bool | None = None,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> WebhookSubscription:
        """Update a per-workspace webhook
        subscription. The bounded path emits a
        `webhook.subscription.updated` audit
        entry with a before/after diff.
        """

        org = str(organization_id)
        existing = await self._subscriptions.get(
            org, subscription_id
        )
        if existing is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        new_name = (
            (name or "").strip()[: self._thresholds.max_name_length]
            if name is not None
            else existing.name
        )
        if not new_name:
            raise WebhookError("WEBHOOK_SUBSCRIPTION_NAME_REQUIRED")
        new_target_url = (
            target_url if target_url is not None else existing.target_url
        )
        if target_url is not None:
            ok, reason = validate_target_url(
                target_url, thresholds=self._thresholds
            )
            if not ok:
                raise WebhookInvalidTargetUrl(reason)
        new_event_types_json = (
            _serialize_event_types(_parse_event_types(event_types))
            if event_types is not None
            else None
        )
        new_enabled = (
            bool(enabled) if enabled is not None else existing.enabled
        )
        updated = await self._subscriptions.update(
            org,
            subscription_id,
            name=new_name,
            target_url=new_target_url,
            event_types_json=new_event_types_json,
            enabled=new_enabled,
        )
        if updated is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        correlation_id = str(uuid4())
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.WEBHOOK_SUBSCRIPTION_UPDATED,
            target=AuditTarget(
                target_type=AuditTargetType.WEBHOOK_SUBSCRIPTION,
                target_id=updated.id,
                display=(
                    f"webhook_subscription:{updated.id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="webhook.subscription.update",
            ),
            metadata=_safe_metadata(
                {
                    "subscription_id": updated.id,
                    "before": {
                        "name": existing.name,
                        "target_url": existing.target_url,
                        "event_types": list(existing.event_types),
                        "enabled": bool(existing.enabled),
                    },
                    "after": {
                        "name": updated.name,
                        "target_url": updated.target_url,
                        "event_types": list(updated.event_types),
                        "enabled": bool(updated.enabled),
                    },
                }
            ),
        )
        return updated

    async def soft_delete_subscription(
        self,
        *,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> None:
        """Soft-delete a per-workspace webhook
        subscription. The bounded path emits a
        `webhook.subscription.deleted` audit
        entry.
        """

        org = str(organization_id)
        existing = await self._subscriptions.get(
            org, subscription_id
        )
        if existing is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        await self._subscriptions.soft_delete(org, subscription_id)
        await self._deliveries.cancel_pending_for_subscription(
            org, subscription_id
        )
        correlation_id = str(uuid4())
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.WEBHOOK_SUBSCRIPTION_DELETED,
            target=AuditTarget(
                target_type=AuditTargetType.WEBHOOK_SUBSCRIPTION,
                target_id=existing.id,
                display=(
                    f"webhook_subscription:{existing.id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="webhook.subscription.delete",
            ),
            metadata=_safe_metadata(
                {
                    "subscription_id": existing.id,
                    "name": existing.name,
                }
            ),
        )

    async def rotate_secret(
        self,
        *,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> WebhookSubscription:
        """Rotate the per-subscription signing
        secret. The bounded path generates a
        new signing secret, persists it
        encrypted via the `US-003`
        `SecretVault`, and emits a
        `webhook.subscription.secret_rotated`
        audit entry.
        """

        if not self._vault:
            raise WebhookError("WEBHOOK_VAULT_REQUIRED")
        if self._environment_mode == EnvironmentMode.PAUSED:
            raise WebhookEnvironmentPaused(
                "WEBHOOK_ENVIRONMENT_PAUSED"
            )
        org = str(organization_id)
        existing = await self._subscriptions.get(
            org, subscription_id
        )
        if existing is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        current = await self._secrets.get_active_for_subscription(
            org, subscription_id
        )
        if current is None:
            raise WebhookError("WEBHOOK_SECRET_NOT_FOUND")
        plaintext_secret = _generate_signing_secret()
        ciphertext = self._vault.encrypt(plaintext_secret)
        new_version = int(current.version) + 1
        rotated = await self._secrets.rotate(
            org, current.id, ciphertext=ciphertext, version=new_version
        )
        if rotated is None:
            raise WebhookError("WEBHOOK_SECRET_NOT_FOUND")
        now = datetime.now(UTC).replace(tzinfo=None)
        updated = await self._subscriptions.mark_rotated(
            org, subscription_id, rotated_at=now
        )
        if updated is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        correlation_id = str(uuid4())
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.WEBHOOK_SUBSCRIPTION_SECRET_ROTATED,
            target=AuditTarget(
                target_type=AuditTargetType.WEBHOOK_SUBSCRIPTION,
                target_id=updated.id,
                display=(
                    f"webhook_subscription:{updated.id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="webhook.subscription.rotate_secret",
            ),
            metadata=_safe_metadata(
                {
                    "subscription_id": updated.id,
                    "secret_id": rotated.id,
                    "version": int(rotated.version),
                    "rotated_at": now.isoformat(),
                }
            ),
        )
        return updated

    async def list_subscriptions(
        self,
        organization_id: UUID | str,
        *,
        enabled: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookSubscription], int]:
        return await self._subscriptions.list_for_org(
            organization_id,
            enabled=enabled,
            limit=limit,
            offset=offset,
        )

    async def get_subscription(
        self,
        organization_id: UUID | str,
        subscription_id: UUID | str,
    ) -> WebhookSubscription | None:
        return await self._subscriptions.get(
            organization_id, subscription_id
        )

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    async def emit_event(
        self,
        *,
        organization_id: UUID | str,
        event_type: WebhookEventType | str,
        event_id: str | None = None,
        payload: dict[str, Any] | None = None,
        actor: str = "system",
        actor_role: str = "system",
    ) -> list[WebhookDelivery]:
        """Emit a bounded webhook event for
        every matching subscription.

        The bounded path reads the matching
        enabled subscriptions, sanitizes the
        payload via `SanitizeAlertPayload`,
        generates the per-subscription signing
        secret via `WebhookSigner`, and
        persists a `WebhookDelivery` row with
        status `pending` for each match.
        """

        if not self._vault:
            raise WebhookError("WEBHOOK_VAULT_REQUIRED")
        if isinstance(event_type, str):
            try:
                event_type = WebhookEventType(event_type)
            except ValueError as exc:
                raise WebhookInvalidEventType(
                    "WEBHOOK_EVENT_TYPE_INVALID"
                ) from exc
        org = str(organization_id)
        sanitized = _payload_sanitized(
            payload or {"event": event_type.value}
        )
        body_payload: dict[str, Any] = {
            "event_type": event_type.value,
            "organization_id": org,
            "event_id": event_id or str(uuid4()),
            "delivered_at": datetime.now(UTC)
            .replace(tzinfo=None)
            .isoformat(),
            "data": sanitized[0],
        }
        body_bytes = build_request_body(body_payload)
        payload_hash = compute_payload_hash(body_bytes)
        subscriptions = await self._subscriptions.list_enabled_for_event(
            org, event_type.value
        )
        deliveries: list[WebhookDelivery] = []
        current = datetime.now(UTC).replace(tzinfo=None)
        for subscription in subscriptions:
            try:
                secret = await self._secrets.get_active_for_subscription(
                    org, subscription.id
                )
            except Exception:  # noqa: BLE001
                continue
            if secret is None:
                continue
            try:
                plaintext = self._vault.decrypt(secret.secret_ciphertext)
            except Exception:  # noqa: BLE001
                continue
            headers = _sign(
                body=body_bytes,
                secret=plaintext,
                timestamp=int(current.timestamp()),
                delivery_id="placeholder",
            )
            _ = headers  # signature is recomputed at dispatch time
            nxt = next_attempt_at(
                attempt_count=0,
                thresholds=self._thresholds,
                now=current,
            )
            delivery = await self._deliveries.add(
                organization_id=org,
                subscription_id=subscription.id,
                event_id=event_id,
                event_type=event_type,
                target_url=subscription.target_url,
                payload_hash=payload_hash,
                request_body=body_bytes.decode("utf-8"),
                signature="",  # recomputed at dispatch time
                status=WebhookDeliveryStatus.PENDING,
                attempt_count=0,
                next_attempt_at=nxt,
                max_response_message_length=(
                    self._thresholds.max_response_message_length
                ),
            )
            deliveries.append(delivery)
        return deliveries

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch_pending(
        self,
        *,
        organization_id: UUID | str | None = None,
        now: datetime | None = None,
    ) -> list[WebhookDelivery]:
        """Dispatch every `pending` and `failed`
        delivery whose `next_attempt_at` has
        elapsed. The bounded path runs the
        `WebhookDispatcher` for each delivery
        and updates the persisted row.
        """

        if not self._vault:
            raise WebhookError("WEBHOOK_VAULT_REQUIRED")
        current = now or datetime.now(UTC).replace(tzinfo=None)
        if organization_id is None:
            deliveries = (
                await self._deliveries.list_pending_for_dispatch(
                    current, limit=200
                )
            )
        else:
            deliveries = (
                await self._deliveries.list_pending_for_org_dispatch(
                    str(organization_id), current, limit=200
                )
            )
        results: list[WebhookDelivery] = []
        for delivery in deliveries:
            secret = await self._secrets.get_active_for_subscription(
                delivery.organization_id, delivery.subscription_id
            )
            if secret is None:
                await self._deliveries.transition_status(
                    delivery.organization_id,
                    delivery.id,
                    status=WebhookDeliveryStatus.DEAD_LETTER,
                    last_response_code=0,
                    last_response_message="signing_secret_missing",
                )
                continue
            try:
                plaintext = self._vault.decrypt(secret.secret_ciphertext)
            except Exception:  # noqa: BLE001
                await self._deliveries.transition_status(
                    delivery.organization_id,
                    delivery.id,
                    status=WebhookDeliveryStatus.DEAD_LETTER,
                    last_response_code=0,
                    last_response_message="signing_secret_invalid",
                )
                continue
            # Mark `in_flight` for the bounded
            # race window. The bounded path
            # uses an atomic SQL update.
            await self._deliveries.mark_in_flight(delivery.id)
            result = await self._dispatcher.dispatch(
                delivery=delivery,
                signing_secret=plaintext,
                now=current,
            )
            updated = await self._deliveries.record_attempt(
                delivery.id,
                status=result.transitioned_to,
                attempt_count=int(delivery.attempt_count) + 1,
                next_attempt_at=result.next_attempt_at,
                last_attempt_at=current,
                last_response_code=None,
                last_response_message=None,
                delivered_at=(
                    current
                    if result.transitioned_to
                    is WebhookDeliveryStatus.SUCCEEDED
                    else None
                ),
                max_response_message_length=(
                    self._thresholds.max_response_message_length
                ),
            )
            if updated is not None:
                results.append(updated)
            await self._emit_delivery_audit(
                delivery=updated or delivery,
                status=result.transitioned_to,
                actor=actor,
                actor_role=actor_role,
            )
        return results

    # ------------------------------------------------------------------
    # Retry / test
    # ------------------------------------------------------------------

    async def retry_delivery(
        self,
        *,
        organization_id: UUID | str,
        delivery_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> WebhookDelivery:
        """Human-confirmed retry for a `failed`
        or `dead_letter` delivery. The bounded
        path transitions the delivery back to
        `pending` and emits a
        `webhook.delivery.retried` audit
        entry.
        """

        org = str(organization_id)
        delivery = await self._deliveries.get(org, delivery_id)
        if delivery is None:
            raise WebhookDeliveryNotFound(
                "WEBHOOK_DELIVERY_NOT_FOUND"
            )
        if delivery.status not in (
            WebhookDeliveryStatus.FAILED,
            WebhookDeliveryStatus.DEAD_LETTER,
        ):
            raise WebhookError("WEBHOOK_DELIVERY_NOT_RETRYABLE")
        correlation_id = str(uuid4())
        current = datetime.now(UTC).replace(tzinfo=None)
        nxt = next_attempt_at(
            attempt_count=0,
            thresholds=self._thresholds,
            now=current,
        )
        updated = await self._deliveries.reset_for_retry(
            org, delivery.id, next_attempt_at=nxt
        )
        if updated is None:
            raise WebhookDeliveryNotFound(
                "WEBHOOK_DELIVERY_NOT_FOUND"
            )
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.WEBHOOK_DELIVERY_RETRIED,
            target=AuditTarget(
                target_type=AuditTargetType.WEBHOOK_DELIVERY,
                target_id=updated.id,
                display=(
                    f"webhook_delivery:{updated.subscription_id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="webhook.delivery.retry",
            ),
            metadata=_safe_metadata(
                {
                    "delivery_id": updated.id,
                    "subscription_id": updated.subscription_id,
                    "event_type": updated.event_type.value,
                    "attempt_count": int(updated.attempt_count),
                }
            ),
        )
        return updated

    async def test_send(
        self,
        *,
        organization_id: UUID | str,
        subscription_id: UUID | str,
        request_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        actor: str = "",
        actor_role: str = "owner",
    ) -> WebhookDelivery:
        """Send a bounded `webhook.test` event
        to the subscription and return the
        delivery result inline.
        """

        if not self._vault:
            raise WebhookError("WEBHOOK_VAULT_REQUIRED")
        org = str(organization_id)
        existing = await self._subscriptions.get(
            org, subscription_id
        )
        if existing is None:
            raise WebhookSubscriptionNotFound(
                "WEBHOOK_SUBSCRIPTION_NOT_FOUND"
            )
        secret = await self._secrets.get_active_for_subscription(
            org, subscription_id
        )
        if secret is None:
            raise WebhookError("WEBHOOK_SECRET_NOT_FOUND")
        plaintext = self._vault.decrypt(secret.secret_ciphertext)
        current = datetime.now(UTC).replace(tzinfo=None)
        body_payload: dict[str, Any] = {
            "event_type": "webhook.test",
            "organization_id": org,
            "event_id": str(uuid4()),
            "delivered_at": current.isoformat(),
            "data": {"test": True},
        }
        body_bytes = build_request_body(body_payload)
        payload_hash = compute_payload_hash(body_bytes)
        nxt = next_attempt_at(
            attempt_count=0,
            thresholds=self._thresholds,
            now=current,
        )
        delivery = await self._deliveries.add(
            organization_id=org,
            subscription_id=subscription_id,
            event_id=None,
            event_type=WebhookEventType.ALERT_FIRED,
            target_url=existing.target_url,
            payload_hash=payload_hash,
            request_body=body_bytes.decode("utf-8"),
            signature="",
            status=WebhookDeliveryStatus.PENDING,
            attempt_count=0,
            next_attempt_at=nxt,
            max_response_message_length=(
                self._thresholds.max_response_message_length
            ),
        )
        await self._deliveries.mark_in_flight(delivery.id)
        result = await self._dispatcher.dispatch(
            delivery=delivery,
            signing_secret=plaintext,
            now=current,
        )
        updated = await self._deliveries.record_attempt(
            delivery.id,
            status=result.transitioned_to,
            attempt_count=1,
            next_attempt_at=result.next_attempt_at,
            last_attempt_at=current,
            last_response_code=None,
            last_response_message=None,
            delivered_at=(
                current
                if result.transitioned_to
                is WebhookDeliveryStatus.SUCCEEDED
                else None
            ),
            max_response_message_length=(
                self._thresholds.max_response_message_length
            ),
        )
        if updated is None:
            raise WebhookDeliveryNotFound(
                "WEBHOOK_DELIVERY_NOT_FOUND"
            )
        correlation_id = str(uuid4())
        await self._audit.emit(
            organization_id=UUID(org),
            actor=make_actor_from_role(
                actor_role, actor_id=actor or None
            ),
            action=AuditAction.WEBHOOK_SUBSCRIPTION_TEST_SENT,
            target=AuditTarget(
                target_type=AuditTargetType.WEBHOOK_SUBSCRIPTION,
                target_id=existing.id,
                display=(
                    f"webhook_subscription:{existing.id}"
                ),
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(
                request_id=request_id,
                correlation_id=correlation_id,
                ip=ip_address,
                user_agent=user_agent,
                workflow="webhook.subscription.test",
            ),
            metadata=_safe_metadata(
                {
                    "subscription_id": existing.id,
                    "delivery_id": updated.id,
                    "status": updated.status.value,
                    "attempt_count": int(updated.attempt_count),
                }
            ),
        )
        return updated

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list_deliveries(
        self,
        organization_id: UUID | str,
        *,
        subscription_id: UUID | str | None = None,
        status: WebhookDeliveryStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookDelivery], int]:
        return await self._deliveries.list_for_org(
            organization_id,
            subscription_id=subscription_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_delivery(
        self,
        organization_id: UUID | str,
        delivery_id: UUID | str,
    ) -> WebhookDelivery | None:
        return await self._deliveries.get(
            organization_id, delivery_id
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _emit_delivery_audit(
        self,
        *,
        delivery: WebhookDelivery,
        status: WebhookDeliveryStatus,
        actor: str = "system",
        actor_role: str = "system",
    ) -> None:
        correlation_id = str(uuid4())
        if status is WebhookDeliveryStatus.SUCCEEDED:
            action = AuditAction.WEBHOOK_DELIVERY_SUCCEEDED
        elif status is WebhookDeliveryStatus.DEAD_LETTER:
            action = AuditAction.WEBHOOK_DELIVERY_DEAD_LETTER
        else:
            action = AuditAction.WEBHOOK_DELIVERY_FAILED
        try:
            await self._audit.emit(
                organization_id=UUID(delivery.organization_id),
                actor=make_actor_from_role(
                    actor_role, actor_id=actor or None
                ),
                action=action,
                target=AuditTarget(
                    target_type=AuditTargetType.WEBHOOK_DELIVERY,
                    target_id=delivery.id,
                    display=(
                        f"webhook_delivery:{delivery.subscription_id}"
                    ),
                ),
                outcome=(
                    AuditOutcome.SUCCEEDED
                    if status is WebhookDeliveryStatus.SUCCEEDED
                    else AuditOutcome.FAILED
                ),
                context=make_context(
                    correlation_id=correlation_id,
                    workflow="webhook.delivery.dispatch",
                ),
                metadata=_safe_metadata(
                    {
                        "delivery_id": delivery.id,
                        "subscription_id": delivery.subscription_id,
                        "event_type": delivery.event_type.value,
                        "attempt_count": int(delivery.attempt_count),
                        "status": delivery.status.value,
                    }
                ),
            )
        except Exception:  # noqa: BLE001
            # Bounded path never lets an audit
            # emission failure break the bounded
            # delivery loop.
            logger.exception(
                "webhook.delivery.audit.emit.failed",
                extra={"delivery_id": delivery.id},
            )


__all__ = [
    "WebhookDeliveryNotFound",
    "WebhookDeliveryService",
    "WebhookEnvironmentPaused",
    "WebhookError",
    "WebhookInvalidEventType",
    "WebhookInvalidPayload",
    "WebhookInvalidTargetUrl",
    "WebhookRetryExhausted",
    "WebhookSubscriptionNotFound",
]
