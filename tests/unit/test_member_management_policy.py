"""Member-management domain rules (US-028)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from livelead.domain.identity import (
    InvitationState,
    MembershipState,
    Role,
    can_invite_member,
    can_manage_member_governance,
    count_active_owners,
    demote_would_lock_organization,
    disable_would_lock_organization,
    generate_invitation_token,
    hash_invitation_token,
    invitation_is_redeemable,
    is_usable_membership,
    revoke_would_lock_organization,
)
from livelead.domain.identity.member_invitations import MemberInvitation


# --- helpers -----------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FakeMembership:
    id: str
    user_id: str
    role: Role
    state: MembershipState = MembershipState.ACTIVE


def _membership(role: Role, state: MembershipState = MembershipState.ACTIVE, mid: str | None = None) -> FakeMembership:
    return FakeMembership(id=mid or str(uuid4()), user_id=str(uuid4()), role=role, state=state)


# --- governance matrix -------------------------------------------------
def test_can_manage_member_governance_owner_can_manage_owners_and_non_owners():
    assert can_manage_member_governance(Role.OWNER, Role.OWNER) is True
    assert can_manage_member_governance(Role.OWNER, Role.ADMIN) is True
    assert can_manage_member_governance(Role.OWNER, Role.VIEWER) is True


def test_can_manage_member_governance_admin_cannot_manage_owners():
    assert can_manage_member_governance(Role.ADMIN, Role.OWNER) is False


def test_can_manage_member_governance_admin_can_manage_non_owners():
    assert can_manage_member_governance(Role.ADMIN, Role.ADMIN) is True
    assert can_manage_member_governance(Role.ADMIN, Role.ANALYST) is True
    assert can_manage_member_governance(Role.ADMIN, Role.VIEWER) is True


def test_can_manage_member_governance_other_roles_cannot_govern():
    for role in (Role.ANALYST, Role.SALES_BD, Role.REVIEWER, Role.VIEWER, Role.COMPLIANCE, None):
        assert can_manage_member_governance(role, Role.ANALYST) is False
        assert can_manage_member_governance(role, Role.OWNER) is False


def test_can_invite_member_for_admins_and_owners():
    assert can_invite_member(Role.OWNER) is True
    assert can_invite_member(Role.ADMIN) is True
    for role in (Role.ANALYST, Role.REVIEWER, Role.VIEWER, Role.SALES_BD):
        assert can_invite_member(role) is False


# --- last-owner protection --------------------------------------------
def test_count_active_owners_ignores_disabled_and_revoked():
    members = [
        _membership(Role.OWNER),
        _membership(Role.OWNER, MembershipState.DISABLED),
        _membership(Role.OWNER, MembershipState.REVOKED),
        _membership(Role.OWNER, MembershipState.PENDING_INVITE),
        _membership(Role.OWNER, MembershipState.EXPIRED),
        _membership(Role.ADMIN),
    ]
    assert count_active_owners(members) == 1


def test_demote_would_lock_organization_with_single_owner():
    only_owner = _membership(Role.OWNER)
    others = [_membership(Role.ADMIN), _membership(Role.ANALYST)]
    members = [only_owner, *others]
    assert demote_would_lock_organization(members, target_membership=only_owner, new_role=Role.ADMIN) is True
    assert demote_would_lock_organization(members, target_membership=only_owner, new_role=Role.VIEWER) is True
    # Promoting / keeping owner does not lock.
    assert demote_would_lock_organization(members, target_membership=only_owner, new_role=Role.OWNER) is False


def test_demote_does_not_lock_when_multiple_owners_exist():
    owner_a = _membership(Role.OWNER)
    owner_b = _membership(Role.OWNER)
    members = [owner_a, owner_b, _membership(Role.ANALYST)]
    assert demote_would_lock_organization(members, target_membership=owner_a, new_role=Role.ADMIN) is False


def test_demote_does_not_lock_when_target_is_not_owner():
    analyst = _membership(Role.ANALYST)
    members = [analyst, _membership(Role.OWNER)]
    assert demote_would_lock_organization(members, target_membership=analyst, new_role=Role.VIEWER) is False


def test_disable_would_lock_organization_blocks_disabling_last_owner():
    only_owner = _membership(Role.OWNER)
    members = [only_owner, _membership(Role.ADMIN)]
    assert disable_would_lock_organization(members, target_membership=only_owner) is True


def test_disable_would_lock_organization_allows_disabling_when_another_owner_remains():
    owner_a = _membership(Role.OWNER)
    owner_b = _membership(Role.OWNER)
    members = [owner_a, owner_b]
    assert disable_would_lock_organization(members, target_membership=owner_a) is False


def test_revoke_would_lock_organization_blocks_revoking_last_owner():
    only_owner = _membership(Role.OWNER)
    members = [only_owner, _membership(Role.ADMIN)]
    assert revoke_would_lock_organization(members, target_membership=only_owner) is True


# --- is_usable_membership ---------------------------------------------
def test_is_usable_membership_only_active_is_usable():
    assert is_usable_membership(_membership(Role.OWNER)) is True
    for state in (
        MembershipState.DISABLED,
        MembershipState.PENDING_INVITE,
        MembershipState.REVOKED,
        MembershipState.EXPIRED,
    ):
        assert is_usable_membership(_membership(Role.OWNER, state)) is False
    assert is_usable_membership(None) is False


# --- invitation token helpers -----------------------------------------
def test_generate_invitation_token_is_url_safe_and_long_enough():
    token = generate_invitation_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    # URL-safe alphabet: no spaces or control characters.
    assert " " not in token
    assert "\n" not in token


def test_hash_invitation_token_is_deterministic_and_hex():
    token = "abc123"
    h1 = hash_invitation_token(token)
    h2 = hash_invitation_token(token)
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_hash_invitation_token_rejects_empty():
    with pytest.raises(ValueError):
        hash_invitation_token("")


def test_invitation_is_redeemable_only_for_pending_unexpired():
    now = datetime.now(UTC)
    pending_unexpired = MemberInvitation(
        id=uuid4(),
        organization_id=uuid4(),
        email="alice@example.com",
        role=Role.ANALYST,
        state=InvitationState.PENDING,
        token_hash="abc",
        invited_by_user_id=None,
        expires_at=now + timedelta(hours=1),
        accepted_by_user_id=None,
        accepted_at=None,
        revoked_at=None,
        revoked_by_user_id=None,
        created_at=now,
        updated_at=now,
    )
    assert invitation_is_redeemable(pending_unexpired, now=now) is True

    pending_expired = MemberInvitation(
        id=pending_unexpired.id,
        organization_id=pending_unexpired.organization_id,
        email=pending_unexpired.email,
        role=pending_unexpired.role,
        state=pending_unexpired.state,
        token_hash=pending_unexpired.token_hash,
        invited_by_user_id=pending_unexpired.invited_by_user_id,
        expires_at=now - timedelta(seconds=1),
        accepted_by_user_id=pending_unexpired.accepted_by_user_id,
        accepted_at=pending_unexpired.accepted_at,
        revoked_at=pending_unexpired.revoked_at,
        revoked_by_user_id=pending_unexpired.revoked_by_user_id,
        created_at=pending_unexpired.created_at,
        updated_at=pending_unexpired.updated_at,
    )
    assert invitation_is_redeemable(pending_expired, now=now) is False

    revoked = MemberInvitation(
        id=pending_unexpired.id,
        organization_id=pending_unexpired.organization_id,
        email=pending_unexpired.email,
        role=pending_unexpired.role,
        state=InvitationState.REVOKED,
        token_hash=pending_unexpired.token_hash,
        invited_by_user_id=pending_unexpired.invited_by_user_id,
        expires_at=pending_unexpired.expires_at,
        accepted_by_user_id=pending_unexpired.accepted_by_user_id,
        accepted_at=pending_unexpired.accepted_at,
        revoked_at=pending_unexpired.revoked_at,
        revoked_by_user_id=pending_unexpired.revoked_by_user_id,
        created_at=pending_unexpired.created_at,
        updated_at=pending_unexpired.updated_at,
    )
    assert invitation_is_redeemable(revoked, now=now) is False

    accepted = MemberInvitation(
        id=pending_unexpired.id,
        organization_id=pending_unexpired.organization_id,
        email=pending_unexpired.email,
        role=pending_unexpired.role,
        state=InvitationState.ACCEPTED,
        token_hash=pending_unexpired.token_hash,
        invited_by_user_id=pending_unexpired.invited_by_user_id,
        expires_at=pending_unexpired.expires_at,
        accepted_by_user_id=pending_unexpired.accepted_by_user_id,
        accepted_at=pending_unexpired.accepted_at,
        revoked_at=pending_unexpired.revoked_at,
        revoked_by_user_id=pending_unexpired.revoked_by_user_id,
        created_at=pending_unexpired.created_at,
        updated_at=pending_unexpired.updated_at,
    )
    assert invitation_is_redeemable(accepted, now=now) is False

    assert invitation_is_redeemable(None) is False  # type: ignore[arg-type]
