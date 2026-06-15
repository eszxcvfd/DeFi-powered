"""Identity-and-access role and membership enums (US-027).

Pure enums, no I/O. The role vocabulary matches the existing
`X-Actor-Role` header values so the legacy header fallback and the audit
log vocabulary stay aligned.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Baseline RBAC roles."""

    OWNER = "owner"
    ADMIN = "admin"
    COMPLIANCE = "compliance"
    ANALYST = "analyst"
    SALES_BD = "sales_bd"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class MembershipState(StrEnum):
    """Membership lifecycle states.

    US-027 added `active` and `disabled`. US-028 extends the lifecycle with
    `pending_invite`, `revoked`, and `expired` so the auth, session, and
    member-management layers can describe a bounded governance path.

    The session resolver treats anything other than `active` as
    non-authenticatable, which is what the US-027 login contract already
    requires.
    """

    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING_INVITE = "pending_invite"
    REVOKED = "revoked"
    EXPIRED = "expired"


_ADMIN_ROLES: frozenset[Role] = frozenset({Role.OWNER, Role.ADMIN})
_GOVERNANCE_ROLES: frozenset[Role] = frozenset(
    {Role.OWNER, Role.ADMIN, Role.COMPLIANCE}
)
_REVIEWER_ROLES: frozenset[Role] = frozenset({Role.OWNER, Role.ADMIN, Role.REVIEWER})
_AUTHENTICATED_ROLES: frozenset[Role] = frozenset(
    {
        Role.OWNER,
        Role.ADMIN,
        Role.COMPLIANCE,
        Role.ANALYST,
        Role.SALES_BD,
        Role.REVIEWER,
        Role.VIEWER,
    }
)


def is_known_role(value: str | Role) -> bool:
    if isinstance(value, Role):
        return True
    try:
        Role(value)
    except ValueError:
        return False
    return True


def parse_role(value: str | Role | None) -> Role | None:
    if value is None:
        return None
    if isinstance(value, Role):
        return value
    try:
        return Role(str(value).strip().lower())
    except ValueError:
        return None


def is_admin(role: Role | None) -> bool:
    return role in _ADMIN_ROLES


def is_owner(role: Role | None) -> bool:
    return role == Role.OWNER


def can_manage_member_governance(actor_role: Role | None, target_role: Role) -> bool:
    """Decide whether the actor may govern the target membership's role.

    Owners may manage owner-level access. Admins may manage non-owner
    access only. The rule mirrors
    `docs/product/member-management-and-access-governance.md`.
    """

    if actor_role is None:
        return False
    if actor_role == Role.OWNER:
        return True
    if actor_role == Role.ADMIN:
        return target_role != Role.OWNER
    return False


def can_invite_member(actor_role: Role | None) -> bool:
    return is_admin(actor_role) or is_governance(actor_role)


def is_governance(role: Role | None) -> bool:
    return role in _GOVERNANCE_ROLES


def is_reviewer(role: Role | None) -> bool:
    return role in _REVIEWER_ROLES


def is_authenticated(role: Role | None) -> bool:
    return role in _AUTHENTICATED_ROLES


def can_access_admin_connector(role: Role | None) -> bool:
    return is_admin(role)


def can_access_browser_profile(role: Role | None) -> bool:
    return is_authenticated(role)


def can_access_audit_log(role: Role | None) -> bool:
    return is_governance(role) or is_admin(role)


def can_review_content(role: Role | None) -> bool:
    return is_reviewer(role)


def can_edit_campaign(role: Role | None) -> bool:
    return role in {Role.OWNER, Role.ADMIN, Role.ANALYST, Role.SALES_BD}


def can_edit_lead_pipeline(role: Role | None) -> bool:
    return role in {Role.OWNER, Role.ADMIN, Role.SALES_BD}


__all__ = [
    "Role",
    "MembershipState",
    "can_manage_member_governance",
    "can_invite_member",
    "is_known_role",
    "parse_role",
    "is_admin",
    "is_governance",
    "is_owner",
    "is_reviewer",
    "is_authenticated",
    "can_access_admin_connector",
    "can_access_browser_profile",
    "can_access_audit_log",
    "can_review_content",
    "can_edit_campaign",
    "can_edit_lead_pipeline",
]
