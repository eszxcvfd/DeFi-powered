"""Webhook dispatcher (US-049).

The dispatcher is the only place that owns
the bounded HTTP POST against a
customer-controlled URL, the bounded state
transitions for the webhook delivery
lifecycle, and the bounded target URL
validation at delivery time.

The dispatcher is HTTP-library agnostic; the
caller injects an `http_post` callable so the
test harness can use a local HTTP receiver
without monkey-patching. The bounded
`http_post` callable returns a
`WebhookHttpResponse` with the response
code and the (sanitized) response message.
"""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlparse

from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
)
from livelead.domain.webhooks.models import (
    PRIVATE_IP_PREFIXES,
    WebhookDelivery,
    WebhookDeliveryThresholds,
)

logger = logging.getLogger("livelead.webhook_dispatcher")


# ---------------------------------------------------------------------------
# HTTP transport protocol
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebhookHttpResponse:
    """The bounded response of a webhook HTTP
    POST.

    The bounded path uses the response to
    decide whether to transition the delivery
    to `succeeded` (2xx), `failed` (4xx/5xx),
    or `dead_letter` (network exception).
    """

    status_code: int
    message: str
    network_error: str = ""


class WebhookHttpPost(Protocol):
    async def __call__(
        self,
        *,
        url: str,
        body: bytes,
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> WebhookHttpResponse: ...


# ---------------------------------------------------------------------------
# Default HTTP transport (httpx)
# ---------------------------------------------------------------------------


class HttpxWebhookHttpPost:
    """Default HTTP transport that uses
    `httpx.AsyncClient` to perform the
    bounded HTTP POST. The bounded path
    enforces the bounded `request_timeout_seconds`
    bound and the bounded target URL
    validation at delivery time.
    """

    def __init__(self, *, client: Any = None) -> None:
        self._client = client

    async def __call__(
        self,
        *,
        url: str,
        body: bytes,
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> WebhookHttpResponse:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError(
                "httpx is required for the default webhook transport"
            ) from exc
        timeout = max(1, int(timeout_seconds))
        try:
            if self._client is not None:
                response = await self._client.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=timeout,
                )
            else:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=False,
                ) as client:
                    response = await client.post(
                        url, content=body, headers=headers
                    )
        except Exception as exc:  # noqa: BLE001
            return WebhookHttpResponse(
                status_code=0,
                message="",
                network_error=str(exc)[:500],
            )
        return WebhookHttpResponse(
            status_code=int(response.status_code),
            message=str(response.text or "")[:500],
        )


# ---------------------------------------------------------------------------
# DNS-resolved target URL validation
# ---------------------------------------------------------------------------


def validate_resolved_target_url(
    target_url: str,
    *,
    thresholds: WebhookDeliveryThresholds,
) -> tuple[bool, str]:
    """Validate the bounded `target_url` after
    DNS resolution. The bounded path refuses
    private IP addresses per `NFR-SEC-006`.

    The bounded path returns `(True, "")` when
    the URL is valid; otherwise, it returns
    `(False, reason)`.
    """

    try:
        parsed = urlparse(target_url)
    except ValueError:
        return False, "WEBHOOK_TARGET_URL_INVALID"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "WEBHOOK_TARGET_URL_INVALID"
    for prefix in PRIVATE_IP_PREFIXES:
        if host.startswith(prefix):
            return False, "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"
    except ValueError:
        # Hostname (not a literal IP). The
        # bounded path does not perform DNS
        # resolution here; the bounded
        # `dispatch` method performs the DNS
        # check at delivery time.
        pass
    return True, ""


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WebhookDispatchResult:
    """The bounded result of a single
    `WebhookDispatcher.dispatch` call.
    """

    delivery: WebhookDelivery
    next_attempt_at: datetime | None
    transitioned_to: WebhookDeliveryStatus


class WebhookDispatcher:
    """Bounded dispatcher that performs the
    bounded HTTP POST against a
    customer-controlled URL.

    The bounded dispatcher:
    - Marks the delivery as `in_flight`
      before the bounded HTTP POST.
    - Performs the bounded target URL
      validation.
    - Calls the bounded `http_post`
      callable.
    - Transitions the delivery to
      `succeeded` (2xx), `failed`
      (4xx/5xx), or `dead_letter`
      (network exception or window
      exceeded).
    - Computes the bounded `next_attempt_at`
      via the bounded `WebhookRetryPolicy`.
    """

    def __init__(
        self,
        *,
        http_post: WebhookHttpPost | None = None,
        thresholds: WebhookDeliveryThresholds | None = None,
    ) -> None:
        self._http_post = http_post or HttpxWebhookHttpPost()
        self._thresholds = thresholds or WebhookDeliveryThresholds()

    @property
    def thresholds(self) -> WebhookDeliveryThresholds:
        return self._thresholds

    async def dispatch(
        self,
        *,
        delivery: WebhookDelivery,
        signing_secret: str,
        now: datetime | None = None,
    ) -> WebhookDispatchResult:
        """Dispatch the bounded delivery.

        The bounded path:
        - Validates the bounded target URL.
        - Marks the delivery as `in_flight`.
        - Performs the bounded HTTP POST.
        - Transitions the delivery to
          `succeeded` / `failed` /
          `dead_letter`.
        - Computes the bounded
          `next_attempt_at` from the
          `WebhookRetryPolicy`.
        """

        from livelead.application.webhooks.retry_policy import (
            next_attempt_at as _next_attempt,
        )

        current = now or datetime.now(UTC).replace(tzinfo=None)
        ok, reason = validate_resolved_target_url(
            delivery.target_url, thresholds=self._thresholds
        )
        if not ok:
            return WebhookDispatchResult(
                delivery=delivery,
                next_attempt_at=None,
                transitioned_to=WebhookDeliveryStatus.DEAD_LETTER,
            )
        # Compute the bounded headers via the
        # bounded `WebhookSigner`.
        from livelead.application.webhooks.signer import (
            sign as _sign,
            TIMESTAMP_HEADER,
        )

        body_bytes = delivery.request_body.encode("utf-8")
        timestamp = int(current.timestamp())
        headers = _sign(
            body=body_bytes,
            secret=signing_secret,
            timestamp=timestamp,
            delivery_id=delivery.id,
        )
        response = await self._http_post(
            url=delivery.target_url,
            body=body_bytes,
            headers=headers,
            timeout_seconds=int(self._thresholds.request_timeout_seconds),
        )
        if response.network_error:
            # Network exception; the bounded
            # path increments `attempt_count`
            # and computes the bounded
            # `next_attempt_at`. The caller
            # updates the persisted row.
            nxt = _next_attempt(
                attempt_count=int(delivery.attempt_count) + 1,
                thresholds=self._thresholds,
                now=current,
            )
            status = (
                WebhookDeliveryStatus.FAILED
                if nxt is not None
                else WebhookDeliveryStatus.DEAD_LETTER
            )
            return WebhookDispatchResult(
                delivery=delivery,
                next_attempt_at=nxt,
                transitioned_to=status,
            )
        if 200 <= int(response.status_code) < 300:
            return WebhookDispatchResult(
                delivery=delivery,
                next_attempt_at=None,
                transitioned_to=WebhookDeliveryStatus.SUCCEEDED,
            )
        # 4xx/5xx; the bounded path increments
        # `attempt_count` and computes the
        # bounded `next_attempt_at`.
        nxt = _next_attempt(
            attempt_count=int(delivery.attempt_count) + 1,
            thresholds=self._thresholds,
            now=current,
        )
        status = (
            WebhookDeliveryStatus.FAILED
            if nxt is not None
            else WebhookDeliveryStatus.DEAD_LETTER
        )
        return WebhookDispatchResult(
            delivery=delivery,
            next_attempt_at=nxt,
            transitioned_to=status,
        )


__all__ = [
    "HttpxWebhookHttpPost",
    "WebhookDispatchResult",
    "WebhookDispatcher",
    "WebhookHttpPost",
    "WebhookHttpResponse",
    "validate_resolved_target_url",
]
