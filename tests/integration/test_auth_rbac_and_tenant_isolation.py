"""Auth-aware RBAC and tenant isolation (US-027)."""

from __future__ import annotations

from uuid import UUID, uuid4

import httpx
import pytest

from livelead.domain.identity import (
    Role,
    hash_email_for_limiter,
    hash_password,
)
from livelead.infrastructure.db.identity_mappers import row_to_user
from livelead.infrastructure.db.models import (
    OrganizationMembershipRow,
    UserRow,
)
from livelead.infrastructure.db.repositories.identity.identity import (
    MembershipRepository,
)


ADMIN_HEADERS = {"X-Actor-Role": "admin"}
ANALYST_HEADERS = {"X-Actor-Role": "analyst"}
REVIEWER_HEADERS = {"X-Actor-Role": "reviewer"}


def _jar(cookies):
    jar = httpx.Cookies()
    for cookie in cookies.jar:
        jar.set(cookie.name, cookie.value, domain=cookie.domain or "test.local")
    return jar


async def _login(client, email: str, password: str = "Hello-World-2026", organization_id: str | None = None):
    body: dict = {"email": email, "password": password}
    if organization_id is not None:
        body["organization_id"] = organization_id
    return await client.post("/auth/login", json=body)


async def _seed(client, *, email: str, password: str, role: Role, organization_id: UUID):
    factory = client.app.state.session_factory
    material = hash_password(password)
    email_hash = hash_email_for_limiter(email)
    async with factory() as sess:
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
        await MembershipRepository(sess).add(
            user_id=user_row.id,
            organization_id=organization_id,
            role=role,
        )
        await sess.commit()
        return row_to_user(user_row).id


async def test_admin_connector_requires_owner_or_admin_role(client):
    # Analyst session must not access admin connector.
    org = "00000000-0000-4000-8000-000000000001"
    await _seed(client, email="rachel@example.com", password="Hello-World-2026", role=Role.ANALYST, organization_id=UUID(org))
    r = await _login(client, "rachel@example.com")
    cookies = _jar(r.cookies)
    denied = await client.get("/admin/connectors", cookies=cookies)
    assert denied.status_code == 403


async def test_admin_connector_allows_admin_session(client):
    org = "00000000-0000-4000-8000-000000000001"
    await _seed(client, email="regina@example.com", password="Hello-World-2026", role=Role.ADMIN, organization_id=UUID(org))
    r = await _login(client, "regina@example.com")
    cookies = _jar(r.cookies)
    ok = await client.get("/admin/connectors", cookies=cookies)
    assert ok.status_code == 200


async def test_audit_log_requires_governance_role(client):
    org = "00000000-0000-4000-8000-000000000001"
    # Analyst should be denied.
    await _seed(client, email="sam@example.com", password="Hello-World-2026", role=Role.ANALYST, organization_id=UUID(org))
    r = await _login(client, "sam@example.com")
    cookies = _jar(r.cookies)
    denied = await client.get("/admin/audit-logs?limit=1", cookies=cookies)
    assert denied.status_code == 403


async def test_audit_log_allows_compliance_role(client):
    org = "00000000-0000-4000-8000-000000000001"
    await _seed(client, email="tara@example.com", password="Hello-World-2026", role=Role.COMPLIANCE, organization_id=UUID(org))
    r = await _login(client, "tara@example.com")
    cookies = _jar(r.cookies)
    ok = await client.get("/admin/audit-logs?limit=1", cookies=cookies)
    assert ok.status_code == 200


async def test_audit_log_cross_tenant_returns_404(client):
    """Reading an audit entry from another organization must return 404."""

    org_a = "00000000-0000-4000-8000-000000000001"
    org_b = "00000000-0000-4000-8000-000000000002"
    # Seed an admin in org A and produce an audit row.
    await _seed(client, email="uma@example.com", password="Hello-World-2026", role=Role.ADMIN, organization_id=UUID(org_a))
    # Seed an org B record so the bootstrap doesn't try to add it.
    factory = client.app.state.session_factory
    from sqlalchemy import text
    async with factory() as sess:
        await sess.execute(text(f"INSERT OR IGNORE INTO organizations (id, name) VALUES ('{org_b}', 'Other Org')"))
        await sess.commit()
        # Now seed an admin in org B.
    await _seed(client, email="victor@example.com", password="Hello-World-2026", role=Role.ADMIN, organization_id=UUID(org_b))
    r2 = await _login(client, "victor@example.com", password="Hello-World-2026", organization_id=org_b)
    r = await _login(client, "uma@example.com")
    cookies = _jar(r.cookies)
    listed = await client.get("/admin/audit-logs?limit=1", cookies=cookies)
    assert listed.status_code == 200
    body = listed.json()
    assert body["items"]
    entry_id = body["items"][0]["id"]

    r2 = await _login(client, "victor@example.com", password="Hello-World-2026", organization_id=org_b)
    cookies2 = _jar(r2.cookies)
    cross = await client.get(f"/admin/audit-logs/{entry_id}", cookies=cookies2)
    assert cross.status_code == 404
    assert cross.json()["detail"] == "audit entry not found"


async def test_logout_invalidates_subsequent_authenticated_calls(client):
    org = "00000000-0000-4000-8000-000000000001"
    await _seed(client, email="wendy@example.com", password="Hello-World-2026", role=Role.OWNER, organization_id=UUID(org))
    r = await _login(client, "wendy@example.com")
    cookies = _jar(r.cookies)
    out = await client.post("/auth/logout", cookies=cookies)
    assert out.status_code == 204
    me = await client.get("/auth/me", cookies=cookies)
    assert me.status_code == 401


async def test_session_cookie_does_not_leak_to_other_role_routes(client):
    """A reviewer session can review content but cannot edit admin-only routes."""

    org = "00000000-0000-4000-8000-000000000001"
    await _seed(client, email="xena@example.com", password="Hello-World-2026", role=Role.REVIEWER, organization_id=UUID(org))
    r = await _login(client, "xena@example.com")
    cookies = _jar(r.cookies)
    # Reviewer can hit /auth/me.
    me = await client.get("/auth/me", cookies=cookies)
    assert me.status_code == 200
    # Reviewer cannot hit admin/connectors.
    denied = await client.get("/admin/connectors", cookies=cookies)
    assert denied.status_code == 403
