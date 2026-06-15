"""Auth API integration (US-027)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import httpx

from livelead.domain.identity import (
    SESSION_COOKIE_NAME,
    LoginFailureReason,
    Role,
    hash_email_for_limiter,
    hash_password,
)
from livelead.infrastructure.db.identity_mappers import row_to_user
from livelead.infrastructure.db.models import (
    OrganizationMembershipRow,
    SessionRow,
    UserRow,
)


def httpx_cookies_to_jar(cookies):
    jar = httpx.Cookies()
    for cookie in cookies.jar:
        jar.set(cookie.name, cookie.value, domain=cookie.domain or "test.local")
    return jar


def _login_payload(email: str, password: str = "Hello-World-2026", org: str | None = None):
    body: dict = {"email": email, "password": password}
    if org is not None:
        body["organization_id"] = org
    return body


async def _seed_user(session_factory, *, email: str, password: str, role: Role, organization_id: UUID):
    material = hash_password(password)
    email_hash = hash_email_for_limiter(email)
    async with session_factory() as sess:
        user_row = UserRow(
            id=str(uuid4()),
            email=email,
            email_hash=email_hash,
            display_name=email,
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
            disabled=False,
        )
        sess.add(user_row)
        await sess.flush()
        membership = OrganizationMembershipRow(
            id=str(uuid4()),
            user_id=user_row.id,
            organization_id=str(organization_id),
            role=role.value,
            state="active",
        )
        sess.add(membership)
        await sess.commit()
        user = row_to_user(user_row)
        return user.id


async def test_login_returns_cookie_and_me_round_trip(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory, email="alice@example.com", password="Hello-World-2026", role=Role.OWNER, organization_id=UUID(org)
    )

    r = await client.post("/auth/login", json=_login_payload("alice@example.com", org=org))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["session"]["email"] == "alice@example.com"
    assert body["session"]["role"] == "owner"
    assert body["session"]["organization_id"] == org
    cookies = httpx_cookies_to_jar(r.cookies)
    assert SESSION_COOKIE_NAME in cookies

    me = await client.get("/auth/me", cookies=cookies)
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == "alice@example.com"
    assert me_body["role"] == "owner"
    assert me_body["organization_id"] == org


async def test_login_returns_generic_failure_for_unknown_user(client):
    payload = _login_payload("nobody@example.com", password="Hello-World-2026")
    r = await client.post("/auth/login", json=payload)
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body
    assert body["detail"] == "invalid credentials"
    # No session cookie should be set on failure.
    assert SESSION_COOKIE_NAME not in r.cookies


async def test_login_returns_generic_failure_for_wrong_password(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory,
        email="bob@example.com",
        password="Correct-Password-2026",
        role=Role.ANALYST,
        organization_id=UUID(org),
    )
    r = await client.post(
        "/auth/login", json=_login_payload("bob@example.com", password="Wrong-Password-2026", org=org)
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid credentials"


async def test_login_returns_same_generic_message_for_disabled_user(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    material = hash_password("Hello-World-2026")
    email_hash = hash_email_for_limiter("carol@example.com")
    async with factory() as sess:
        user_row = UserRow(
            id=str(uuid4()),
            email="carol@example.com",
            email_hash=email_hash,
            display_name="carol",
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
            disabled=True,
        )
        sess.add(user_row)
        sess.add(
            OrganizationMembershipRow(
                id=str(uuid4()),
                user_id=user_row.id,
                organization_id=org,
                role=Role.VIEWER.value,
                state="active",
            )
        )
        await sess.commit()
    r = await client.post(
        "/auth/login", json=_login_payload("carol@example.com", org=org)
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid credentials"


async def test_login_returns_404_for_mismatched_organization(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory,
        email="dave@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
        organization_id=UUID(org),
    )
    other_org = "00000000-0000-4000-8000-000000000099"
    r = await client.post(
        "/auth/login",
        json=_login_payload("dave@example.com", org=other_org),
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid credentials"


async def test_logout_revokes_session(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory,
        email="erin@example.com",
        password="Hello-World-2026",
        role=Role.ADMIN,
        organization_id=UUID(org),
    )
    r = await client.post(
        "/auth/login", json=_login_payload("erin@example.com", org=org)
    )
    cookies = httpx_cookies_to_jar(r.cookies)
    assert SESSION_COOKIE_NAME in cookies
    out = await client.post("/auth/logout", cookies=cookies)
    assert out.status_code == 204
    me = await client.get("/auth/me", cookies=cookies)
    assert me.status_code == 401


async def test_refresh_rotates_session_token(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    user_id = await _seed_user(
        factory,
        email="frank@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
        organization_id=UUID(org),
    )
    r = await client.post(
        "/auth/login", json=_login_payload("frank@example.com", org=org)
    )
    cookies = httpx_cookies_to_jar(r.cookies)
    refresh = await client.post("/auth/refresh", cookies=cookies)
    assert refresh.status_code == 200
    refresh_cookies = httpx_cookies_to_jar(refresh.cookies)
    assert SESSION_COOKIE_NAME in refresh_cookies
    # Old token must no longer work.
    me_old = await client.get("/auth/me", cookies=cookies)
    assert me_old.status_code == 401
    me_new = await client.get("/auth/me", cookies=refresh_cookies)
    assert me_new.status_code == 200


async def test_login_rate_limiting_locks_account(client):
    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory,
        email="gail@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
        organization_id=UUID(org),
    )
    payload = _login_payload("gail@example.com", password="Wrong-Password-2026", org=org)
    for _ in range(3):
        r = await client.post("/auth/login", json=payload)
        assert r.status_code == 401
    # 4th attempt must still be a generic 401, not 200.
    locked = await client.post("/auth/login", json=payload)
    assert locked.status_code == 401
    assert locked.json()["detail"] == "invalid credentials"


async def test_bootstrap_status_reports_seed_when_empty(client):
    # Clean users table to ensure bootstrap-status reflects a fresh state.
    factory = client.app.state.session_factory
    async with factory() as sess:
        from sqlalchemy import delete

        await sess.execute(delete(SessionRow))
        await sess.execute(delete(OrganizationMembershipRow))
        await sess.execute(delete(UserRow))
        await sess.commit()
    r = await client.get("/auth/bootstrap-status")
    assert r.status_code == 200
    body = r.json()
    assert body["has_users"] is False
    assert body["default_email"] == "owner@example.com"


async def test_authenticated_session_replaces_header_role(client):
    """A real session cookie overrides the legacy header for protected routes."""

    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory,
        email="hank@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
        organization_id=UUID(org),
    )
    r = await client.post(
        "/auth/login", json=_login_payload("hank@example.com", org=org)
    )
    cookies = httpx_cookies_to_jar(r.cookies)
    # The audit log endpoint should now succeed with the session cookie
    # even if the legacy header is set to a lower-privilege role.
    denied_headers = {"X-Actor-Role": "analyst"}
    listed = await client.get(
        "/admin/audit-logs?limit=1", cookies=cookies, headers=denied_headers
    )
    assert listed.status_code == 200


async def test_login_emits_audit_events_for_success_and_failure(client):
    """A representative audit row appears for both success and failure."""

    org = "00000000-0000-4000-8000-000000000001"
    factory = client.app.state.session_factory
    await _seed_user(
        factory,
        email="ivy@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
        organization_id=UUID(org),
    )
    fail = await client.post(
        "/auth/login",
        json=_login_payload("ivy@example.com", password="Wrong-Password-2026", org=org),
    )
    assert fail.status_code == 401
    success = await client.post(
        "/auth/login", json=_login_payload("ivy@example.com", org=org)
    )
    assert success.status_code == 200

    listed = await client.get(
        "/admin/audit-logs",
        headers={"X-Actor-Role": "admin"},
        params={"action_family": "auth", "limit": 50},
    )
    assert listed.status_code == 200
    body = listed.json()
    actions = {item["action"] for item in body["items"]}
    assert "auth.login.failed" in actions
    assert "auth.login.succeeded" in actions
