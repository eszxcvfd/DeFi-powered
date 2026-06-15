"""Member management API integration (US-028)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from livelead.domain.identity import (
    InvitationState,
    MembershipState,
    Role,
    SESSION_COOKIE_NAME,
    hash_email_for_limiter,
    hash_password,
)
from livelead.infrastructure.db.identity_mappers import row_to_membership
from livelead.infrastructure.db.models import (
    MemberInvitationRow,
    OrganizationMembershipRow,
    SessionRow,
    UserRow,
)
from livelead.infrastructure.db.repositories.identity.identity import (
    MemberInvitationRepository,
    MembershipRepository,
    SessionRepository,
    UserRepository,
)


ADMIN = {"X-Actor-Role": "admin"}
ANALYST = {"X-Actor-Role": "analyst"}
OWNER = {"X-Actor-Role": "owner"}
ORG = "00000000-0000-4000-8000-000000000001"


async def _login(client, *, email: str, password: str, role: Role, organization_id: str = ORG) -> dict:
    factory = client.app.state.session_factory
    # Wipe the bootstrap owner so we can claim a clean email namespace.
    from sqlalchemy import delete
    from livelead.infrastructure.db.models import OrganizationMembershipRow as _OMR, UserRow as _UR
    from livelead.domain.identity import MembershipState as _MS
    async with factory() as sess:
        await sess.execute(delete(_OMR))
        await sess.execute(delete(_UR).where(_UR.email == "owner@example.com"))
        await sess.commit()

    material = hash_password(password)
    email_hash = hash_email_for_limiter(email)
    async with factory() as sess:
        user = UserRow(
            id=str(uuid4()),
            email=email,
            email_hash=email_hash,
            display_name=email,
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
            disabled=False,
        )
        sess.add(user)
        await sess.flush()
        sess.add(
            OrganizationMembershipRow(
                id=str(uuid4()),
                user_id=user.id,
                organization_id=organization_id,
                role=role.value,
                state=MembershipState.ACTIVE.value,
            )
        )
        await sess.commit()

    r = await client.post(
        "/auth/login",
        json={"email": email, "password": password, "organization_id": organization_id},
    )
    assert r.status_code == 200, r.text
    return dict(r.cookies)


async def _existing_member(client, *, email: str, role: Role, organization_id: str = ORG) -> str:
    factory = client.app.state.session_factory
    material = hash_password("Hello-World-2026")
    email_hash = hash_email_for_limiter(email)
    async with factory() as sess:
        user = UserRow(
            id=str(uuid4()),
            email=email,
            email_hash=email_hash,
            display_name=email,
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
            disabled=False,
        )
        sess.add(user)
        await sess.flush()
        membership = OrganizationMembershipRow(
            id=str(uuid4()),
            user_id=user.id,
            organization_id=organization_id,
            role=role.value,
            state=MembershipState.ACTIVE.value,
        )
        sess.add(membership)
        await sess.commit()
        return str(user.id), str(membership.id)


# --- listing & RBAC ---------------------------------------------------
@pytest.mark.asyncio
async def test_member_listing_is_role_gated(client):
    # Owner can list.
    owner_cookies = await _login(client, email="owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    r = await client.get("/admin/members", cookies=owner_cookies)
    assert r.status_code == 200
    body = r.json()
    assert "members" in body and "invitations" in body
    assert body["total_members"] == 1

    # Admin can list.
    admin_cookies = await _login(client, email="admin@example.com", password="Hello-World-2026", role=Role.ADMIN)
    r_admin = await client.get("/admin/members", cookies=admin_cookies)
    assert r_admin.status_code == 200

    # Analyst (authenticated, lower-privilege) must be denied.
    analyst_cookies = await _login(client, email="watcher@example.com", password="Hello-World-2026", role=Role.VIEWER)
    r_analyst = await client.get("/admin/members", cookies=analyst_cookies)
    assert r_analyst.status_code == 403

    # Anonymous request must be denied.
    from httpx import ASGITransport, AsyncClient
    from apps.api.main import create_app as _create_app
    fresh_app = _create_app()
    fresh_transport = ASGITransport(app=fresh_app)
    from asgi_lifespan import LifespanManager
    async with LifespanManager(fresh_app):
        async with AsyncClient(transport=fresh_transport, base_url="http://test") as fresh:
            denied = await fresh.get("/admin/members", headers=ANALYST)
            assert denied.status_code == 401


# --- invitation lifecycle -------------------------------------------
@pytest.mark.asyncio
async def test_invite_create_list_revoke_and_redact_token_in_audit(client):
    cookies = await _login(client, email="owner2@example.com", password="Hello-World-2026", role=Role.OWNER)

    # Create the invite.
    r = await client.post(
        "/admin/members/invitations",
        cookies=cookies,
        json={"email": "newbie@example.com", "role": "analyst"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["invitation"]["email"] == "newbie@example.com"
    assert body["invitation"]["role"] == "analyst"
    assert body["invitation"]["state"] == "pending"
    assert body["invite_token"] and len(body["invite_token"]) >= 32
    invitation_id = body["invitation"]["id"]
    token = body["invite_token"]

    # Listing shows the new pending invite.
    listed = await client.get("/admin/members", cookies=cookies)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["total_invitations"] == 1
    assert listed_body["invitations"][0]["email"] == "newbie@example.com"

    # Revoke the invite.
    revoke = await client.post(
        f"/admin/members/invitations/{invitation_id}/revoke",
        cookies=cookies,
        json={"reason": "wrong recipient"},
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["invitation"]["state"] == "revoked"

    # The token is now unusable.
    accept = await client.post(
        "/auth/invitations/accept",
        json={"token": token, "password": "Hello-World-2026"},
    )
    assert accept.status_code == 410
    assert accept.json()["detail"]["code"] == "invite_revoked"

    # Audit log must mention the invite + revoke actions without leaking
    # the token in metadata.
    audit = await client.get(
        "/admin/audit-logs",
        headers=OWNER,
        params={"action_family": "member", "limit": 50},
    )
    assert audit.status_code == 200
    items = audit.json()["items"]
    actions = {item["action"] for item in items}
    assert "member.invited" in actions
    assert "member.invitation.revoked" in actions
    for item in items:
        meta = item["metadata"]
        if "invitation_id" in meta:
            assert meta["invitation_id"] == invitation_id
        # Token must never appear in audit metadata.
        for value in meta.values():
            assert token not in str(value)


# --- acceptance creates user + membership + session ----------------
@pytest.mark.asyncio
async def test_invite_acceptance_creates_user_and_membership(client):
    cookies = await _login(client, email="owner3@example.com", password="Hello-World-2026", role=Role.OWNER)
    r = await client.post(
        "/admin/members/invitations",
        cookies=cookies,
        json={"email": "newcomer@example.com", "role": "reviewer"},
    )
    assert r.status_code == 201
    token = r.json()["invite_token"]

    accept = await client.post(
        "/auth/invitations/accept",
        json={"token": token, "password": "Hello-World-2026", "display_name": "New Comer"},
    )
    assert accept.status_code == 200, accept.text
    body = accept.json()
    assert body["role"] == "reviewer"
    assert body["organization_id"] == ORG
    assert body["new_user"] is True

    # The session cookie is set so the new user is signed in immediately.
    assert SESSION_COOKIE_NAME in accept.cookies
    me = await client.get("/auth/me", cookies=dict(accept.cookies))
    assert me.status_code == 200
    assert me.json()["email"] == "newcomer@example.com"


# --- role change governance + last-owner protection -----------------
@pytest.mark.asyncio
async def test_role_change_blocks_demote_last_owner(client):
    cookies = await _login(client, email="solo-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    factory = client.app.state.session_factory
    async with factory() as sess:
        member_repo = MembershipRepository(sess)
        memberships = await member_repo.list_for_organization(UUID(ORG))
        solo_membership_id = next(m.id for m in memberships if m.role == Role.OWNER)

    change = await client.patch(
        f"/admin/members/{solo_membership_id}",
        cookies=cookies,
        json={"role": "admin"},
    )
    assert change.status_code == 409
    assert change.json()["detail"]["code"] == "last_owner_protected"

    audit = await client.get(
        "/admin/audit-logs",
        headers=OWNER,
        params={"action": "member.governance.denied", "limit": 10},
    )
    actions = {item["action"] for item in audit.json()["items"]}
    assert "member.governance.denied" in actions


@pytest.mark.asyncio
async def test_role_change_allows_demote_when_second_owner_exists(client):
    cookies = await _login(client, email="alpha@example.com", password="Hello-World-2026", role=Role.OWNER)
    _, second_membership_id = await _existing_member(
        client, email="bravo@example.com", role=Role.OWNER
    )
    change = await client.patch(
        f"/admin/members/{second_membership_id}",
        cookies=cookies,
        json={"role": "admin"},
    )
    assert change.status_code == 200, change.text
    assert change.json()["member"]["role"] == "admin"


@pytest.mark.asyncio
async def test_admin_cannot_manage_owner_role(client):
    cookies = await _login(client, email="root-admin@example.com", password="Hello-World-2026", role=Role.ADMIN)
    _, owner_membership_id = await _existing_member(
        client, email="root-owner@example.com", role=Role.OWNER
    )
    change = await client.patch(
        f"/admin/members/{owner_membership_id}",
        cookies=cookies,
        json={"role": "analyst"},
    )
    assert change.status_code == 409
    assert change.json()["detail"]["code"] == "role_not_governable"


# --- disable / revoke / session invalidation ------------------------
@pytest.mark.asyncio
async def test_disable_member_invalidates_active_session(client):
    # Owner creates a member, then signs in as that member.
    owner_cookies = await _login(client, email="chief@example.com", password="Hello-World-2026", role=Role.OWNER)
    new_user_id, membership_id = await _existing_member(
        client, email="disabled-user@example.com", role=Role.ANALYST
    )
    # Issue a real session for the new user.
    login = await client.post(
        "/auth/login",
        json={"email": "disabled-user@example.com", "password": "Hello-World-2026", "organization_id": ORG},
    )
    assert login.status_code == 200
    user_cookies = dict(login.cookies)

    me_before = await client.get("/auth/me", cookies=user_cookies)
    assert me_before.status_code == 200

    # Owner disables the member.
    disable = await client.post(
        f"/admin/members/{membership_id}/disable",
        cookies=owner_cookies,
    )
    assert disable.status_code == 200, disable.text
    body = disable.json()
    assert body["member"]["state"] == "disabled"
    assert body["sessions_revoked"] >= 1

    # The now-disabled user's session must no longer authenticate.
    me_after = await client.get("/auth/me", cookies=user_cookies)
    assert me_after.status_code == 401

    # And a fresh login attempt is rejected with the generic 401.
    fresh = await client.post(
        "/auth/login",
        json={"email": "disabled-user@example.com", "password": "Hello-World-2026", "organization_id": ORG},
    )
    assert fresh.status_code == 401
    assert fresh.json()["detail"] == "invalid credentials"


@pytest.mark.asyncio
async def test_revoke_member_access_marks_revoked_and_revokes_sessions(client):
    owner_cookies = await _login(client, email="chief2@example.com", password="Hello-World-2026", role=Role.OWNER)
    _, membership_id = await _existing_member(
        client, email="to-revoke@example.com", role=Role.ANALYST
    )
    revoke = await client.delete(
        f"/admin/members/{membership_id}",
        cookies=owner_cookies,
    )
    assert revoke.status_code == 200
    body = revoke.json()
    assert body["member"]["state"] == "revoked"
    assert body["sessions_revoked"] >= 0  # no active session was issued in this test


@pytest.mark.asyncio
async def test_enable_member_restores_active_state(client):
    owner_cookies = await _login(client, email="chief3@example.com", password="Hello-World-2026", role=Role.OWNER)
    user_id, membership_id = await _existing_member(
        client, email="to-enable@example.com", role=Role.ANALYST
    )
    await client.post(f"/admin/members/{membership_id}/disable", cookies=owner_cookies)
    enable = await client.post(
        f"/admin/members/{membership_id}/enable",
        cookies=owner_cookies,
    )
    assert enable.status_code == 200
    assert enable.json()["member"]["state"] == "active"


# --- duplicate email guards -----------------------------------------
@pytest.mark.asyncio
async def test_invite_to_existing_member_email_is_rejected(client):
    cookies = await _login(client, email="owner4@example.com", password="Hello-World-2026", role=Role.OWNER)
    await _existing_member(client, email="already-here@example.com", role=Role.ANALYST)
    r = await client.post(
        "/admin/members/invitations",
        cookies=cookies,
        json={"email": "already-here@example.com", "role": "analyst"},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "email_already_member"


@pytest.mark.asyncio
async def test_duplicate_pending_invite_is_rejected(client):
    cookies = await _login(client, email="owner5@example.com", password="Hello-World-2026", role=Role.OWNER)
    payload = {"email": "double-pending@example.com", "role": "analyst"}
    r1 = await client.post("/admin/members/invitations", cookies=cookies, json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/admin/members/invitations", cookies=cookies, json=payload)
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] in {"invalid_state", "email_already_member"}


# --- acceptance edge cases ------------------------------------------
@pytest.mark.asyncio
async def test_accept_with_short_password_is_rejected(client):
    cookies = await _login(client, email="owner6@example.com", password="Hello-World-2026", role=Role.OWNER)
    r = await client.post(
        "/admin/members/invitations",
        cookies=cookies,
        json={"email": "shorty@example.com", "role": "analyst"},
    )
    assert r.status_code == 201
    token = r.json()["invite_token"]
    # Password fails the pydantic min_length=12 check first; the public
    # service still surfaces the failure as a 4xx with the same code.
    accept = await client.post(
        "/auth/invitations/accept",
        json={"token": token, "password": "short"},
    )
    assert accept.status_code in (400, 422)


@pytest.mark.asyncio
async def test_accept_unknown_token_returns_not_found(client):
    accept = await client.post(
        "/auth/invitations/accept",
        json={"token": "this-token-does-not-exist-1234567890", "password": "Hello-World-2026"},
    )
    assert accept.status_code == 404
    assert accept.json()["detail"]["code"] == "not_found"
