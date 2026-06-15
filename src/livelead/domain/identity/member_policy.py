"""Member-management pure policy helpers (US-028).

These functions are intentionally side-effect free. The application
service in `livelead.application.member_management` owns the
side effects (database writes, audit rows, session revocation); this
module encodes the rules that decide what is allowed.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from .member_invitations import InvitationState
from .roles import MembershipState, Role


def is_usable_membership(membership: Any) -> bool:
    """A membership is "usable" for authentication and product reads.

    `pending_invite`, `disabled`, `revoked`, and `expired` memberships
    are not usable. The auth layer relies on this contract.
    """

    if membership is None:
        return False
    state = getattr(membership, "state", None)
    return state == MembershipState.ACTIVE


def is_actor_administrative(actor_role: Role | None) -> bool:
    return actor_role in (Role.OWNER, Role.ADMIN)


def is_owner_membership(membership: Any) -> bool:
    if membership is None:
        return False
    role = getattr(membership, "role", None)
    return role == Role.OWNER


def count_active_owners(memberships: Iterable[Any]) -> int:
    """Count active owner memberships in one organization."""

    total = 0
    for membership in memberships:
        if not is_usable_membership(membership):
            continue
        if is_owner_membership(membership):
            total += 1
    return total


def demote_would_lock_organization(
    memberships: Iterable[Any],
    *,
    target_membership: Any,
    new_role: Role,
) -> bool:
    """Decide whether a role change would remove the last active owner.

    Returns True when the proposed role change for `target_membership`
    would leave the organization with zero active owners.
    """

    if not is_owner_membership(target_membership):
        return False
    if new_role == Role.OWNER:
        return False
    # Snapshot of the membership set with the proposed change applied.
    projected = []
    for membership in memberships:
        if getattr(membership, "id", None) == getattr(target_membership, "id", None):
            projected.append(_clone_with_role(membership, new_role))
        else:
            projected.append(membership)
    return count_active_owners(projected) == 0


def disable_would_lock_organization(
    memberships: Iterable[Any],
    *,
    target_membership: Any,
) -> bool:
    if not is_owner_membership(target_membership):
        return False
    projected = []
    for membership in memberships:
        if getattr(membership, "id", None) == getattr(target_membership, "id", None):
            projected.append(_clone_with_state(membership, MembershipState.DISABLED))
        else:
            projected.append(membership)
    return count_active_owners(projected) == 0


def revoke_would_lock_organization(
    memberships: Iterable[Any],
    *,
    target_membership: Any,
) -> bool:
    if not is_owner_membership(target_membership):
        return False
    projected = []
    for membership in memberships:
        if getattr(membership, "id", None) == getattr(target_membership, "id", None):
            projected.append(_clone_with_state(membership, MembershipState.REVOKED))
        else:
            projected.append(membership)
    return count_active_owners(projected) == 0


def invitation_is_redeemable(invitation: Any, *, now: datetime | None = None) -> bool:
    if invitation is None:
        return False
    state = getattr(invitation, "state", None)
    if state != InvitationState.PENDING:
        return False
    expires_at = getattr(invitation, "expires_at", None)
    if expires_at is None:
        return False
    current = now or datetime.now(UTC)
    return expires_at > current


def _clone_with_role(membership: Any, role: Role) -> Any:
    if hasattr(membership, "__class__") and hasattr(membership, "__dataclass_fields__"):
        from dataclasses import replace

        return replace(membership, role=role)
    return membership


def _clone_with_state(membership: Any, state: MembershipState) -> Any:
    if hasattr(membership, "__class__") and hasattr(membership, "__dataclass_fields__"):
        from dataclasses import replace

        return replace(membership, state=state)
    return membership


__all__ = [
    "is_usable_membership",
    "is_actor_administrative",
    "is_owner_membership",
    "count_active_owners",
    "demote_would_lock_organization",
    "disable_would_lock_organization",
    "revoke_would_lock_organization",
    "invitation_is_redeemable",
]
