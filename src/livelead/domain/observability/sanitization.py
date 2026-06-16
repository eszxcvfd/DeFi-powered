"""Sanitize alert payloads (US-041).

The contract is simple: any payload that may end up on an
`AlertEvent` row, an in-app notification, or an email body must
pass through `sanitize_alert_payload` first. The function reuses
the audit-log redaction from `livelead.domain.audit.redaction` so
secret, cookie, PII, and full-connection-string material is
stripped in one place. The wrapper enforces the size cap that
the rule payload contract advertises and returns a tuple with a
boolean so the caller can record the redaction flag on the
event.
"""

from __future__ import annotations

from typing import Any

from livelead.domain.audit.redaction import (
    REDACTED,
    enforce_size_cap,
    is_sensitive_key,
    redact_metadata,
)


def _contains_redacted_value(value: Any) -> bool:
    """Walk a redacted payload and return True if any value was replaced."""

    if isinstance(value, dict):
        return any(_contains_redacted_value(v) for v in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_redacted_value(v) for v in value)
    if isinstance(value, str):
        return value == REDACTED or value.startswith("[REDACTED")
    return False


def sanitize_alert_payload(payload: Any) -> tuple[dict[str, Any], bool]:
    """Sanitize a payload, returning the cleaned copy and a redaction flag.

    The flag is `True` when at least one sensitive key or value was
    removed, or when the size cap truncated the payload. Operators
    read the flag from the alert event row so a payload that looks
    suspiciously small is explainable.
    """

    if payload is None:
        return {}, False
    if not isinstance(payload, dict):
        return enforce_size_cap({"value": str(payload)}), False
    redacted = redact_metadata(payload)
    # The flag is set when:
    # - a sensitive key was present (the value or its replacement is REDACTED)
    # - redact_metadata replaced a value with [REDACTED] (e.g. high-entropy match)
    # - the size cap truncated the payload
    redacted_flag = (
        any(is_sensitive_key(str(k)) for k in payload)
        or _contains_redacted_value(redacted)
    )
    capped = enforce_size_cap(redacted)
    if capped is not redacted:
        redacted_flag = True
    return capped, bool(redacted_flag)


__all__ = ["sanitize_alert_payload"]
