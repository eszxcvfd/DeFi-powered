"""Webhook delivery domain models (US-049).

Pure dataclasses with no I/O. The infrastructure
layer is responsible for translating these to and
from SQLAlchemy rows. The model layer deliberately
does not import SQLAlchemy, FastAPI, or any
framework.

The model layer reuses the closed
`WebhookEventType` and `WebhookDeliveryStatus`
enums. The `WebhookDeliveryService` is the only
place that mutates `webhook_subscriptions` and
`webhook_deliveries`; the REST layer calls it
from the request handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
    WebhookEventType,
)


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebhookSubscription:
    """A single record of a per-workspace
    webhook subscription.

    The row carries enough information for the
    bounded `WebhookDeliveryService` to
    dispatch a delivery against the closed
    retry policy without reading raw tables.
    """

    id: str
    organization_id: str
    name: str
    target_url: str
    secret_id: str
    event_types: tuple[str, ...]
    enabled: bool
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_rotated_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    deleted_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "target_url": self.target_url,
            "secret_id": self.secret_id,
            "event_types": list(self.event_types),
            "enabled": bool(self.enabled),
            "created_by": self.created_by,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "last_rotated_at": (
                self.last_rotated_at.isoformat()
                if self.last_rotated_at
                else None
            ),
            "last_success_at": (
                self.last_success_at.isoformat()
                if self.last_success_at
                else None
            ),
            "last_failure_at": (
                self.last_failure_at.isoformat()
                if self.last_failure_at
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebhookDelivery:
    """A single record of a per-delivery history.

    The table is bounded to the most recent N
    deliveries per subscription so a flapping
    subscription cannot fill the table.
    """

    id: str
    organization_id: str
    subscription_id: str
    event_id: str | None
    event_type: WebhookEventType
    target_url: str
    payload_hash: str
    request_body: str
    signature: str
    status: WebhookDeliveryStatus
    attempt_count: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    last_response_code: int | None
    last_response_message: str | None
    delivered_at: datetime | None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "subscription_id": self.subscription_id,
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "target_url": self.target_url,
            "payload_hash": self.payload_hash,
            "status": self.status.value,
            "attempt_count": int(self.attempt_count),
            "next_attempt_at": (
                self.next_attempt_at.isoformat()
                if self.next_attempt_at
                else None
            ),
            "last_attempt_at": (
                self.last_attempt_at.isoformat()
                if self.last_attempt_at
                else None
            ),
            "last_response_code": self.last_response_code,
            "last_response_message": self.last_response_message,
            "delivered_at": (
                self.delivered_at.isoformat()
                if self.delivered_at
                else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Secret
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebhookSigningSecret:
    """A single record of a per-subscription
    signing secret.

    The secret is stored encrypted via the
    `US-003` `SecretVault`; the bounded
    service never returns the plaintext in
    any response payload.
    """

    id: str
    organization_id: str
    subscription_id: str
    secret_ciphertext: str
    version: int
    created_at: datetime | None = None
    rotated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebhookDeliveryThresholds:
    """The closed set of thresholds the bounded
    webhook delivery surface reads.

    The thresholds follow the defaults documented
    in `docs/product/webhook-delivery-and-event-fanout.md`
    and are exposed as a single dataclass so a
    future story can extend the surface with
    per-tenant tuning without redefining the
    contract.
    """

    max_attempts: int = 6
    initial_backoff_seconds: int = 30
    backoff_multiplier: float = 2.0
    max_backoff_seconds: int = 3600
    jitter_seconds: int = 30
    request_timeout_seconds: int = 30
    max_recent_deliveries_per_subscription: int = 100
    max_response_message_length: int = 500
    max_target_url_length: int = 2048
    max_event_types_per_subscription: int = 16
    max_name_length: int = 200
    max_payload_size_bytes: int = 1024 * 1024
    signature_replay_window_seconds: int = 300
    pilot_live_max_window_seconds: int = 24 * 3600
    test_like_max_window_seconds: int = 3600
    paused_max_window_seconds: int = 3600
    min_window_seconds: int = 60

    def max_window_seconds_for_mode(self, mode) -> int:
        """Return the closed `max_window_seconds`
        bound for the bounded `EnvironmentMode`.

        The follow-on per-tenant story can extend
        this method with explicit per-tenant
        tuning; the first slice follows the closed
        bound.
        """
        from livelead.domain.runtime.enums import EnvironmentMode

        if mode is EnvironmentMode.PILOT_LIVE:
            return self.pilot_live_max_window_seconds
        return self.test_like_max_window_seconds


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


# The closed set of URL schemes the bounded
# `WebhookSubscription.target_url` validation
# accepts. The bounded path refuses other
# schemes.
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset(
    {"https", "http"}
)

# The closed set of host patterns the bounded
# `WebhookSubscription.target_url` validation
# allows for the `http` scheme. The bounded
# path only accepts `http://localhost` for
# development; production deployments must
# use `https://`.
LOCALHOST_HOSTS: frozenset[str] = frozenset(
    {"localhost", "127.0.0.1", "::1"}
)

# The closed set of host patterns the bounded
# `WebhookSubscription.target_url` validation
# refuses. The bounded path refuses metadata
# service endpoints and link-local hostnames.
METADATA_SERVICE_HOSTS: frozenset[str] = frozenset(
    {"169.254.169.254"}
)

# The closed set of IP address ranges the
# bounded `WebhookSubscription.target_url`
# validation refuses per `NFR-SEC-006`.
PRIVATE_IP_PREFIXES: tuple[str, ...] = (
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
    "169.254.",
    "127.",
    "0.",
    "::",
    "fe80:",
    "fc",
    "fd",
)

__all__ = [
    "ALLOWED_URL_SCHEMES",
    "LOCALHOST_HOSTS",
    "METADATA_SERVICE_HOSTS",
    "PRIVATE_IP_PREFIXES",
    "WebhookDelivery",
    "WebhookDeliveryThresholds",
    "WebhookSigningSecret",
    "WebhookSubscription",
]
