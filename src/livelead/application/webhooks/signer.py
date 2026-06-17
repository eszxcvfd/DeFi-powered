"""Webhook signer (US-049).

The signer is the only place that owns the
HMAC-SHA256 signing, the timestamp header,
the `X-Webhook-Id` header, the
`X-Webhook-Timestamp` header, and the
`X-Webhook-Signature` header. The helper is
pure; it does not touch the database or
the network.

The bounded path uses a constant-time
comparison helper for the verifier side to
defend against timing attacks. The bounded
path rejects signatures whose timestamp is
more than `signature_replay_window_seconds`
in the past or in the future to defend
against replay attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

from livelead.domain.webhooks.models import (
    WebhookDeliveryThresholds,
)

logger = logging.getLogger("livelead.webhook_signer")


SIGNATURE_VERSION = "v1"
SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"
ID_HEADER = "X-Webhook-Id"


def sign(
    *,
    body: bytes,
    secret: str,
    timestamp: int,
    delivery_id: str,
) -> dict[str, str]:
    """Compute the bounded HMAC-SHA256
    signature for the body and return the
    bounded header set.

    The bounded path computes
    `HMAC-SHA256(secret, "{timestamp}.{body}")`
    hex-encoded and returns the bounded
    header set:
    - `X-Webhook-Id: {delivery_id}`
    - `X-Webhook-Timestamp: {timestamp}`
    - `X-Webhook-Signature: v1,{hex_signature}`
    """

    if not secret:
        raise ValueError("WEBHOOK_SIGNER_INVALID_SECRET")
    if not delivery_id:
        raise ValueError("WEBHOOK_SIGNER_INVALID_DELIVERY_ID")
    payload = f"{timestamp}.".encode() + (body or b"")
    digest = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return {
        ID_HEADER: delivery_id,
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: f"{SIGNATURE_VERSION},{digest}",
    }


def verify(
    *,
    body: bytes,
    secret: str,
    timestamp_header: str,
    signature_header: str,
    delivery_id_header: str,
    now: int | None = None,
    thresholds: WebhookDeliveryThresholds | None = None,
) -> bool:
    """Verify the bounded HMAC-SHA256
    signature with constant-time comparison
    and the bounded replay window.

    The bounded path returns `False` when:
    - the secret is missing
    - the timestamp is missing or
      non-integer
    - the signature is missing or
      malformed
    - the timestamp is outside the bounded
      replay window
    - the constant-time comparison fails
    """

    if not secret or not signature_header:
        return False
    if not timestamp_header or not delivery_id_header:
        return False
    try:
        timestamp = int(timestamp_header)
    except (TypeError, ValueError):
        return False
    current = int(now if now is not None else time.time())
    window = (
        thresholds.signature_replay_window_seconds
        if thresholds is not None
        else WebhookDeliveryThresholds().signature_replay_window_seconds
    )
    if abs(current - timestamp) > window:
        return False
    if not signature_header.startswith(f"{SIGNATURE_VERSION},"):
        return False
    expected_hex = signature_header[len(SIGNATURE_VERSION) + 1 :]
    payload = f"{timestamp}.".encode() + (body or b"")
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, expected_hex)


def compute_payload_hash(body: bytes) -> str:
    """Compute the bounded SHA-256 hash of the
    request body. The bounded path uses the
    hash to identify duplicate deliveries
    and to detect in-flight replays.
    """

    return hashlib.sha256(body or b"").hexdigest()


def build_request_body(
    payload: dict[str, Any],
) -> bytes:
    """Build the bounded JSON request body.

    The bounded path uses a stable JSON
    encoding (no extra whitespace) so the
    hash is deterministic across retries.
    """

    import json

    return json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


__all__ = [
    "ID_HEADER",
    "SIGNATURE_HEADER",
    "SIGNATURE_VERSION",
    "TIMESTAMP_HEADER",
    "build_request_body",
    "compute_payload_hash",
    "sign",
    "verify",
]
