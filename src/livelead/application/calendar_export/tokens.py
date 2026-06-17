"""Calendar export token hashing helpers (US-045).

The token plaintext is never persisted. The service hashes
the plaintext at mint time and stores the hash on the
`calendar_export_tokens` row. The bounded path resolves
the token at request time by hashing the presented
plaintext and looking up the row by `token_hash`. The
helper uses HMAC-SHA-256 with a process-local salt because
the calendar export token is a low-entropy secret that
the service needs to verify on every ICS request. The
contract is "compare a presented token against the
stored hash" so a future story can swap the algorithm
without re-opening the surface.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import string


def _token_salt() -> bytes:
    salt = os.environ.get("LIVELEAD_CALENDAR_TOKEN_SALT", "livelead-default-calendar-salt")
    return salt.encode("utf-8")


def hash_calendar_token(plaintext: str) -> str:
    """Hash a calendar export token with HMAC-SHA-256."""

    candidate = str(plaintext or "")
    h = hmac.new(_token_salt(), candidate.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def verify_calendar_token(plaintext: str, stored_hash: str) -> bool:
    """Constant-time compare of a presented token against the stored hash."""

    candidate = hash_calendar_token(plaintext)
    return hmac.compare_digest(candidate, stored_hash or "")


def mint_calendar_token_plaintext() -> str:
    """Mint a fresh calendar export token plaintext.

    The plaintext uses a URL-safe alphabet so the token
    can travel in a calendar subscription URL without
    escaping. The default length is 32 characters which
    gives 190 bits of entropy, well above the 128-bit
    threshold recommended for short-lived bearer
    tokens.
    """

    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(32))


__all__ = [
    "hash_calendar_token",
    "mint_calendar_token_plaintext",
    "verify_calendar_token",
]
