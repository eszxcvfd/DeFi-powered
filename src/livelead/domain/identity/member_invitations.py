"""Member invitation domain types (US-028)."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .roles import Role

INVITATION_TOKEN_BYTES = 32
INVITATION_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days


class InvitationState(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


def generate_invitation_token() -> str:
    """Generate an opaque, URL-safe random invitation token."""

    return secrets.token_urlsafe(INVITATION_TOKEN_BYTES)


def hash_invitation_token(token: str) -> str:
    """SHA-256 hex digest of the cleartext invitation token.

    Persisted in the database so a database leak does not yield a usable
    invitation. The cleartext is only ever returned to the inviter at
    creation time and to the invitee at acceptance time.
    """

    if not token:
        raise ValueError("token must not be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MemberInvitation:
    """Pending invitation from an inviter to one email address.

    Invitations are scoped to one organization, one email, and one
    intended role. Acceptance must not become a privilege-escalation
    path: the redeemer inherits the invitation's role.
    """

    id: UUID
    organization_id: UUID
    email: str
    role: Role
    state: InvitationState
    token_hash: str
    invited_by_user_id: UUID | None
    expires_at: datetime
    accepted_by_user_id: UUID | None
    accepted_at: datetime | None
    revoked_at: datetime | None
    revoked_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    def is_pending(self, now: datetime | None = None) -> bool:
        if self.state != InvitationState.PENDING:
            return False
        current = now or datetime.now(UTC)
        return self.expires_at > current

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "email": self.email,
            "role": self.role.value,
            "state": self.state.value,
            "invited_by_user_id": (
                str(self.invited_by_user_id) if self.invited_by_user_id else ""
            ),
            "expires_at": self.expires_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else "",
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else "",
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class InvitationAcceptanceResult:
    """Result of redeeming an invitation token.

    `user_id` is the user who accepted the invite (existing or newly
    created). `membership_id` is the resulting organization membership.
    `access_token` and `session_expires_at` are optional: when present
    the redeemer is automatically signed in on the new organization so
    the acceptance flow does not require a separate login.
    """

    user_id: UUID
    membership_id: UUID
    role: Role
    organization_id: UUID
    access_token: str | None = None
    session_expires_at: datetime | None = None
    new_user: bool = False


@dataclass(frozen=True, slots=True)
class MemberManagementError:
    """Public, non-revealing reasons returned at the HTTP boundary.

    The audit layer may record a more specific internal reason, but the
    HTTP response only ever shows one of the public values.
    """

    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    INVALID_STATE = "invalid_state"
    LAST_OWNER_PROTECTED = "last_owner_protected"
    INVITE_EXPIRED = "invite_expired"
    INVITE_REVOKED = "invite_revoked"
    INVITE_ALREADY_ACCEPTED = "invite_already_accepted"
    ROLE_NOT_GOVERNABLE = "role_not_governable"
    EMAIL_ALREADY_MEMBER = "email_already_member"
    INVALID_PAYLOAD = "invalid_payload"


@dataclass(frozen=True, slots=True)
class MemberListing:
    members: list[Any]  # OrganizationMembership domain types
    invitations: list[MemberInvitation]


def new_invitation_id() -> UUID:
    return uuid4()


def default_invitation_ttl(seconds: int = INVITATION_TTL_SECONDS):
    from datetime import timedelta

    return timedelta(seconds=seconds)


__all__ = [
    "INVITATION_TOKEN_BYTES",
    "INVITATION_TTL_SECONDS",
    "InvitationState",
    "MemberInvitation",
    "InvitationAcceptanceResult",
    "MemberManagementError",
    "MemberListing",
    "generate_invitation_token",
    "hash_invitation_token",
    "new_invitation_id",
    "default_invitation_ttl",
]
