"""Audit metadata redaction (US-026).

Secret-safe: never persist raw credential material, full cookies, access tokens,
or oversized raw payloads. Redaction is deterministic: any field whose name
matches a sensitive key pattern OR whose stringified value matches a sensitive
value pattern is replaced by the literal string ``[REDACTED]``.

This module is pure — no I/O — so it can be unit-tested in isolation.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

# Field-name patterns (case-insensitive substring match).
_SENSITIVE_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"passwd", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"apikey", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"session[_-]?secret", re.IGNORECASE),
    re.compile(r"refresh[_-]?token", re.IGNORECASE),
)

# Value patterns that always look like a credential even if the key is generic.
_SENSITIVE_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^sk[-_][A-Za-z0-9\-_]{16,}$"),
    re.compile(r"^pk[-_][A-Za-z0-9\-_]{16,}$"),
    re.compile(r"^Bearer\s+[A-Za-z0-9._\-]{8,}$", re.IGNORECASE),
    re.compile(r"^Basic\s+[A-Za-z0-9+/=]{8,}$", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z_\-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{16,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{8,}"),
    # 32+ char hex or base64 strings of high entropy are almost always secrets
    re.compile(r"^[A-Fa-f0-9]{32,}$"),
    re.compile(r"^[A-Za-z0-9+/=_\-]{40,}$"),
)

# Hard caps so we never persist huge raw payloads inside audit metadata.
_MAX_STR_LEN = 240
_MAX_LIST_ITEMS = 20
_MAX_TOTAL_BYTES = 8_192


def is_sensitive_key(name: str) -> bool:
    return any(p.search(name or "") for p in _SENSITIVE_KEY_PATTERNS)


def is_sensitive_value(value: str) -> bool:
    s = (value or "").strip()
    if not s:
        return False
    return any(p.match(s) for p in _SENSITIVE_VALUE_PATTERNS)


def _truncate_str(value: str) -> str:
    if len(value) <= _MAX_STR_LEN:
        return value
    return value[:_MAX_STR_LEN] + "…"


def _redact_value(value: Any, *, parent_key: str = "") -> Any:
    """Recursively redact a value, returning a JSON-serializable shape."""

    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if is_sensitive_key(str(k)):
                out[str(k)] = REDACTED
            else:
                out[str(k)] = _redact_value(v, parent_key=str(k))
        return out
    if isinstance(value, (list, tuple)):
        items = [_redact_value(v, parent_key=parent_key) for v in list(value)[:_MAX_LIST_ITEMS]]
        if len(value) > _MAX_LIST_ITEMS:
            items.append(f"…({len(value) - _MAX_LIST_ITEMS} more redacted)")
        return items
    if isinstance(value, str):
        if is_sensitive_value(value):
            return REDACTED
        return _truncate_str(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    # Unknown types -> coerced to redacted string for safety.
    return REDACTED


def redact_metadata(value: Any) -> Any:
    """Public entry point. Returns a JSON-safe copy of *value* with secrets removed."""

    try:
        import json

        json.dumps(_redact_value(value))
        return _redact_value(value)
    except (TypeError, ValueError):
        return REDACTED


def total_size(value: Any) -> int:
    """Approximate serialized size used to enforce a hard cap on metadata."""

    import json

    try:
        return len(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return _MAX_TOTAL_BYTES + 1


def enforce_size_cap(value: Any) -> Any:
    """If metadata exceeds the hard cap, collapse it to a short notice."""

    if total_size(value) <= _MAX_TOTAL_BYTES:
        return value
    return {"truncated": True, "original_size_bytes": total_size(value), "cap": _MAX_TOTAL_BYTES}
