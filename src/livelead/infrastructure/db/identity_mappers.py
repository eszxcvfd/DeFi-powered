"""ORM -> domain mapping for identity and access (US-027 + US-028)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from livelead.domain.identity import (
    InvitationState,
    MemberInvitation,
    MembershipState,
    OrganizationMembership,
    Role,
    Session,
    User,
)
from livelead.infrastructure.db.models import (
    MemberInvitationRow,
    OrganizationMembershipRow,
    SessionRow,
    UserRow,
)


def _uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def row_to_user(row: UserRow) -> User:
    return User(
        id=_uuid(row.id),
        email=row.email,
        email_hash=row.email_hash,
        display_name=row.display_name or "",
        password_hash=row.password_hash,
        password_salt=row.password_salt,
        password_iterations=int(row.password_iterations or 0),
        disabled=bool(row.disabled),
        failed_attempts=int(row.failed_attempts or 0),
        locked_until=_ensure_utc(row.locked_until),
        last_login_at=_ensure_utc(row.last_login_at),
        created_at=_ensure_utc(row.created_at) or datetime.now(UTC),
        updated_at=_ensure_utc(row.updated_at) or datetime.now(UTC),
    )


def row_to_membership(row: OrganizationMembershipRow) -> OrganizationMembership:
    role = Role(str(row.role).strip().lower()) if row.role else Role.VIEWER
    state = MembershipState(str(row.state).strip().lower()) if row.state else MembershipState.ACTIVE
    return OrganizationMembership(
        id=_uuid(row.id),
        user_id=_uuid(row.user_id),
        organization_id=_uuid(row.organization_id),
        role=role,
        state=state,
        created_at=_ensure_utc(row.created_at) or datetime.now(UTC),
        updated_at=_ensure_utc(row.updated_at) or datetime.now(UTC),
    )


def row_to_session(row: SessionRow) -> Session:
    role = Role(str(row.role).strip().lower()) if row.role else Role.VIEWER
    return Session(
        id=_uuid(row.id),
        user_id=_uuid(row.user_id),
        organization_id=_uuid(row.organization_id),
        role=role,
        token_hash=row.token_hash,
        issued_at=_ensure_utc(row.issued_at) or datetime.now(UTC),
        expires_at=_ensure_utc(row.expires_at) or datetime.now(UTC),
        last_seen_at=_ensure_utc(row.last_seen_at),
        rotated_at=_ensure_utc(row.rotated_at),
        revoked_at=_ensure_utc(row.revoked_at),
        client_ip=row.client_ip or "",
        user_agent=row.user_agent or "",
    )


def row_to_member_invitation(row: MemberInvitationRow) -> MemberInvitation:
    role = Role(str(row.role).strip().lower()) if row.role else Role.VIEWER
    state = (
        InvitationState(str(row.state).strip().lower())
        if row.state
        else InvitationState.PENDING
    )
    return MemberInvitation(
        id=_uuid(row.id),
        organization_id=_uuid(row.organization_id),
        email=str(row.email or "").strip().lower(),
        role=role,
        state=state,
        token_hash=row.token_hash or "",
        invited_by_user_id=_uuid(row.invited_by_user_id) if row.invited_by_user_id else None,
        expires_at=_ensure_utc(row.expires_at) or datetime.now(UTC),
        accepted_by_user_id=_uuid(row.accepted_by_user_id) if row.accepted_by_user_id else None,
        accepted_at=_ensure_utc(row.accepted_at),
        revoked_at=_ensure_utc(row.revoked_at),
        revoked_by_user_id=_uuid(row.revoked_by_user_id) if row.revoked_by_user_id else None,
        created_at=_ensure_utc(row.created_at) or datetime.now(UTC),
        updated_at=_ensure_utc(row.updated_at) or datetime.now(UTC),
    )


__all__ = [
    "row_to_user",
    "row_to_membership",
    "row_to_session",
    "row_to_member_invitation",
]
