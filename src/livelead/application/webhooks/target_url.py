"""Webhook target URL validator (US-049).

The validator is the only place that owns
the bounded target URL validation against
the closed URL allowlist:

- The `target_url` must start with `https://`
  or `http://localhost`.
- The `target_url` must not resolve to a
  private IP address (RFC 1918 ranges,
  loopback, link-local, multicast, or
  reserved) per `NFR-SEC-006`.
- The `target_url` must not be a metadata
  service endpoint (`169.254.169.254`).
- The `target_url` must not be longer than
  `max_target_url_length` characters.

The validator is pure; it does not touch the
database or the network. The bounded path
returns a tuple `(ok, reason)` so the
caller can record the rejection reason in
the audit log.
"""

from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

from livelead.domain.webhooks.models import (
    ALLOWED_URL_SCHEMES,
    LOCALHOST_HOSTS,
    METADATA_SERVICE_HOSTS,
    PRIVATE_IP_PREFIXES,
    WebhookDeliveryThresholds,
)

logger = logging.getLogger("livelead.webhook_target_url_validator")


def validate_target_url(
    target_url: str,
    *,
    thresholds: WebhookDeliveryThresholds | None = None,
) -> tuple[bool, str]:
    """Validate the bounded `target_url`.

    The bounded path returns `(True, "")` when
    the URL is valid; otherwise, it returns
    `(False, reason)` where `reason` is one
    of the closed `WEBHOOK_TARGET_URL_*`
    codes.
    """

    if not target_url or not isinstance(target_url, str):
        return False, "WEBHOOK_TARGET_URL_INVALID"
    if len(target_url) > int(
        thresholds.max_target_url_length
        if thresholds is not None
        else WebhookDeliveryThresholds().max_target_url_length
    ):
        return False, "WEBHOOK_TARGET_URL_TOO_LONG"
    try:
        parsed = urlparse(target_url)
    except ValueError:
        return False, "WEBHOOK_TARGET_URL_INVALID"
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        return False, "WEBHOOK_TARGET_URL_SCHEME_INVALID"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "WEBHOOK_TARGET_URL_INVALID"
    if scheme == "http" and host not in LOCALHOST_HOSTS:
        return False, "WEBHOOK_TARGET_URL_HTTP_NOT_LOCALHOST"
    if scheme == "https":
        # Refuse metadata service endpoints.
        if host in METADATA_SERVICE_HOSTS:
            return False, "WEBHOOK_TARGET_URL_METADATA_BLOCKED"
        # Refuse obvious private IP literals.
        for prefix in PRIVATE_IP_PREFIXES:
            if host.startswith(prefix):
                return False, "WEBHOOK_TARGET_URL_PRIVATE_BLOCKED"
        # Try to parse as an IP address to catch
        # IPv6 private ranges and other reserved
        # ranges the simple prefix check misses.
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
            # resolution to keep the validator
            # pure; the dispatcher performs the
            # DNS check at delivery time.
            pass
    return True, ""


__all__ = [
    "validate_target_url",
]
