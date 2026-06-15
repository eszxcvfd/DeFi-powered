"""Session token and session model helpers (US-027)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from livelead.domain.identity import MembershipState, Role


SESSION_TOKEN_BYTES = 32
SESSION_COOKIE_NAME = "livelead_session"
SESSION_TTL_SECONDS = 8 * 60 * 60  # 8 hours
SESSION_REFRESH_LEEWAY_SECONDS = 60
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # hard cap on refresh


def generate_session_token() -> str:
    """Generate an opaque, URL-safe random session token."""

    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """SHA-256 hex digest of the cleartext session token.

    Persisted in the database so a database leak does not yield a usable
    session token. The cleartext is only ever returned to the caller at
    login and refresh.
    """

    if not token:
        raise ValueError("token must not be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    email_hash: str
    display_name: str
    password_hash: str
    password_salt: str
    password_iterations: int
    disabled: bool
    failed_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class OrganizationMembership:
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: Role
    state: MembershipState
    created_at: datetime
    updated_at: datetime

    def is_active(self) -> bool:
        return self.state == MembershipState.ACTIVE


@dataclass(frozen=True, slots=True)
class Session:
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: Role
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    last_seen_at: datetime | None
    rotated_at: datetime | None
    revoked_at: datetime | None
    client_ip: str
    user_agent: str

    def is_active(self, now: datetime | None = None) -> bool:
        if self.revoked_at is not None:
            return False
        current = now or datetime.now(UTC)
        return self.expires_at > current

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "organization_id": str(self.organization_id),
            "role": self.role.value,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    """What the rest of the system needs from the auth boundary."""

    user_id: UUID
    email: str
    display_name: str
    organization_id: UUID
    role: Role
    session_id: UUID
    expires_at: datetime

    def to_summary(self) -> dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "display_name": self.display_name,
            "organization_id": str(self.organization_id),
            "role": self.role.value,
            "session_id": str(self.session_id),
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class LoginFailureReason:
    """Generic, non-revealing login failure reasons used at the API boundary.

    The audit layer may record a more specific internal reason, but the
    HTTP response only ever shows one of the public values.
    """

    INVALID_CREDENTIALS = "invalid_credentials"
    LOCKED = "locked"
    RATE_LIMITED = "rate_limited"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


def new_session_id() -> UUID:
    return uuid4()


def default_session_ttl(seconds: int = SESSION_TTL_SECONDS) -> timedelta:
    return timedelta(seconds=seconds)


__all__ = [
    "SESSION_TOKEN_BYTES",
    "SESSION_COOKIE_NAME",
    "SESSION_TTL_SECONDS",
    "SESSION_REFRESH_LEEWAY_SECONDS",
    "SESSION_MAX_AGE_SECONDS",
    "generate_session_token",
    "hash_session_token",
    "constant_time_eq",
    "User",
    "OrganizationMembership",
    "Session",
    "AuthenticatedIdentity",
    "LoginFailureReason",
    "new_session_id",
    "default_session_ttl",
]
