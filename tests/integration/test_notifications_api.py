"""Notification API integration (US-029)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import json

from livelead.domain.identity import (
    MembershipState,
    Role,
    hash_email_for_limiter,
    hash_password,
)
from livelead.domain.notifications import (
    DEFAULT_EMAIL_PREFERENCES,
    DEFAULT_IN_APP_PREFERENCES,
    NotificationState,
    NotificationType,
)
from livelead.infrastructure.db.models import (
    EventRow,
    FollowUpReminderRow,
    LeadRow,
    OrganizationMembershipRow,
    UserNotificationRow,
    UserRow,
)
from livelead.infrastructure.db.repositories.notifications import (
    NotificationPreferenceRepository,
    UserNotificationRepository,
)
from livelead.infrastructure.notifications import (
    EmailRequest,
    EmailResult,
    InMemoryEmailProvider,
    NotificationProviderAdapter,
)
from livelead.application.notifications import (
    NotificationService,
    reminder_candidates_for,
    discovery_job_candidates_for,
)


ADMIN = {"X-Actor-Role": "admin"}
ANALYST = {"X-Actor-Role": "analyst"}
ORG = "00000000-0000-4000-8000-000000000001"


async def _login(client, *, email: str, password: str, role: Role, organization_id: str = ORG) -> dict:
    factory = client.app.state.session_factory
    from sqlalchemy import delete
    from livelead.infrastructure.db.models import (
        OrganizationMembershipRow as _OMR,
        UserRow as _UR,
    )
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


async def _seed_in_app_notification(
    client, *, user_id: str, n_type: NotificationType = NotificationType.JOB_COMPLETED
) -> str:
    factory = client.app.state.session_factory
    async with factory() as sess:
        row = UserNotificationRow(
            id=str(uuid4()),
            organization_id=ORG,
            user_id=user_id,
            notification_type=n_type.value,
            state=NotificationState.UNREAD.value,
            source_record_type="system",
            source_record_id="seed",
            title="Seeded notification",
            summary="Seed summary",
            deep_link="/",
        )
        sess.add(row)
        await sess.commit()
        return str(row.id)


# --- inbox / read / dismiss -----------------------------------------
@pytest.mark.asyncio
async def test_inbox_listing_and_unread_count(client):
    cookies = await _login(client, email="notif-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    me = await client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]

    seeded_id = await _seed_in_app_notification(client, user_id=user_id)

    listed = await client.get("/notifications", cookies=cookies)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    assert body["items"][0]["id"] == seeded_id

    # Mark as read.
    read = await client.post(f"/notifications/{seeded_id}/read", cookies=cookies)
    assert read.status_code == 200
    assert read.json()["state"] == "read"

    # Dismiss.
    dismiss = await client.post(f"/notifications/{seeded_id}/dismiss", cookies=cookies)
    assert dismiss.status_code == 200
    assert dismiss.json()["state"] == "dismissed"


@pytest.mark.asyncio
async def test_inbox_is_tenant_and_user_scoped(client):
    cookies = await _login(client, email="scope-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    me = await client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]
    other_id = await _seed_in_app_notification(client, user_id=user_id)

    # Build a second user in a different org and confirm the inbox never
    # exposes their notification.
    factory = client.app.state.session_factory
    other_org = "00000000-0000-4000-8000-000000000777"
    async with factory() as sess:
        material = hash_password("Hello-World-2026")
        other_user_id = str(uuid4())
        other_email = f"other-{uuid4().hex[:6]}@example.com"
        other_user = UserRow(
            id=other_user_id,
            email=other_email,
            email_hash=hash_email_for_limiter(other_email),
            display_name=other_email,
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
            disabled=False,
        )
        sess.add(other_user)
        await sess.flush()
        sess.add(
            OrganizationMembershipRow(
                id=str(uuid4()),
                user_id=other_user_id,
                organization_id=other_org,
                role=Role.OWNER.value,
                state=MembershipState.ACTIVE.value,
            )
        )
        await sess.commit()

    other_seed = await _seed_in_app_notification(client, user_id=other_user_id)

    inbox = await client.get("/notifications", cookies=cookies)
    assert inbox.status_code == 200
    inbox_ids = {n["id"] for n in inbox.json()["items"]}
    assert other_id in inbox_ids
    assert other_seed not in inbox_ids


# --- preferences ----------------------------------------------------
@pytest.mark.asyncio
async def test_preferences_default_seed_and_update(client):
    cookies = await _login(client, email="pref-owner@example.com", password="Hello-World-2026", role=Role.OWNER)

    initial = await client.get("/notification-preferences", cookies=cookies)
    assert initial.status_code == 200
    body = initial.json()
    # First read seeds the matrix.
    assert body["is_seeded"] is True
    types = {p["notification_type"] for p in body["preferences"]}
    assert NotificationType.EVENT_UPCOMING.value in types
    assert NotificationType.JOB_FAILED.value in types
    seeded_event = next(
        p for p in body["preferences"] if p["notification_type"] == "event_upcoming"
    )
    assert seeded_event["in_app_enabled"] is True
    assert seeded_event["email_enabled"] is True

    # Update preferences to disable event-upcoming email.
    update = await client.patch(
        "/notification-preferences",
        cookies=cookies,
        json={
            "preferences": {
                "event_upcoming": {"in_app": True, "email": False},
                "reminder_overdue": {"email": True},
            }
        },
    )
    assert update.status_code == 200
    updated_body = update.json()
    overrides = {
        p["notification_type"]: p for p in updated_body["preferences"]
    }
    assert overrides["event_upcoming"]["email_enabled"] is False
    assert overrides["reminder_overdue"]["email_enabled"] is True

    # Audit log must mention the preference change without leaking values.
    audit = await client.get(
        "/admin/audit-logs",
        headers=ADMIN,
        params={"action_family": "notification", "limit": 50},
    )
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert "notification.preference_changed" in actions


@pytest.mark.asyncio
async def test_preference_update_rejects_unknown_type(client):
    cookies = await _login(client, email="pref-bad@example.com", password="Hello-World-2026", role=Role.OWNER)
    r = await client.patch(
        "/notification-preferences",
        cookies=cookies,
        json={"preferences": {"unknown_type": {"in_app": True}}},
    )
    assert r.status_code == 400


# --- service + email provider --------------------------------------
@pytest.mark.asyncio
async def test_notification_service_delivers_in_app_and_email(client):
    cookies = await _login(client, email="service-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    me = await client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]

    factory = client.app.state.session_factory
    provider = InMemoryEmailProvider()
    async with factory() as sess:
        svc = NotificationService(sess, email_provider=provider)
        matrix = await svc.get_or_seed_preferences(
            organization_id=UUID(ORG), user_id=UUID(user_id)
        )
        # Event upcoming is email-eligible by default.
        views = await svc.deliver_candidate(
            request=None,
            candidate=next(
                iter(
                    [
                        v
                        for v in (
                            await _build_event_candidate(
                                UUID(ORG), UUID(user_id), UUID(me.json()["user_id"]))
                        )
                    ]
                )
            ) if False else _event_candidate(UUID(ORG), UUID(user_id)),
            actor_role=Role.OWNER,
        )
        assert any(v.delivery is not None for v in views)
        assert any(v.delivery is None for v in views)
        assert provider.sent, "email provider should have recorded the attempt"
        await sess.commit()

    # Inbox now contains the in-app row.
    inbox = await client.get("/notifications", cookies=cookies)
    assert inbox.json()["total"] >= 1
    assert inbox.json()["unread_count"] >= 1


@pytest.mark.asyncio
async def test_notification_service_suppresses_email_when_disabled(client):
    cookies = await _login(client, email="suppress-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    me = await client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]

    factory = client.app.state.session_factory
    provider = InMemoryEmailProvider()
    async with factory() as sess:
        pref_repo = NotificationPreferenceRepository(sess)
        # Disable email for event_upcoming only.
        await pref_repo.upsert(
            organization_id=UUID(ORG),
            user_id=UUID(user_id),
            notification_type=NotificationType.EVENT_UPCOMING,
            in_app_enabled=True,
            email_enabled=False,
        )
        await sess.commit()

        svc = NotificationService(sess, email_provider=provider)
        views = await svc.deliver_candidate(
            request=None,
            candidate=_event_candidate(UUID(ORG), UUID(user_id)),
            actor_role=Role.OWNER,
        )
        # In-app is created, email is suppressed.
        assert any(v.delivery is None for v in views)
        assert all(v.delivery is None for v in views)
        assert provider.sent == []  # no email attempt
        await sess.commit()


@pytest.mark.asyncio
async def test_email_provider_failure_path_records_diagnostic(client):
    cookies = await _login(client, email="fail-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    me = await client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]

    factory = client.app.state.session_factory
    provider = InMemoryEmailProvider(fail_recipients={"fail-owner@example.com"})
    async with factory() as sess:
        svc = NotificationService(sess, email_provider=provider)
        views = await svc.deliver_candidate(
            request=None,
            candidate=_event_candidate(UUID(ORG), UUID(user_id)),
            actor_role=Role.OWNER,
        )
        assert any(v.delivery is not None and v.delivery.status.value == "failed" for v in views)
        await sess.commit()

    # Audit must mention the failed delivery without leaking the email
    # address.
    audit = await client.get(
        "/admin/audit-logs",
        headers=ADMIN,
        params={"action_family": "notification", "limit": 50},
    )
    failed = [
        item for item in audit.json()["items"]
        if item["action"] == "notification.delivery_failed"
    ]
    assert failed, "expected a delivery-failed audit row"
    for row in failed:
        for value in row["metadata"].values():
            assert "fail-owner@example.com" not in str(value)


# --- admin scan endpoint -------------------------------------------
@pytest.mark.asyncio
async def test_admin_scan_creates_event_upcoming_notifications(client):
    cookies = await _login(client, email="scan-owner@example.com", password="Hello-World-2026", role=Role.OWNER)
    me = await client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]

    factory = client.app.state.session_factory
    starts_at = datetime.now(UTC) + timedelta(minutes=10)
    async with factory() as sess:
        event = EventRow(
            id=str(uuid4()),
            organization_id=ORG,
            campaign_id=str(uuid4()),
            canonical_title="Acme Event",
            source_url="https://example.com/events/acme",
            observed_at=datetime.now(UTC),
            starts_at=starts_at,
        )
        sess.add(event)
        await sess.commit()

    scan = await client.post(
        "/admin/notifications/scan",
        cookies=cookies,
        json={"include_reminders": False, "include_events": True, "lead_minutes": 60},
    )
    assert scan.status_code == 200, scan.text
    body = scan.json()
    assert body["candidates"] >= 1
    assert body["in_app_created"] >= 1
    assert body["emails_attempted"] >= 1

    inbox = await client.get("/notifications", cookies=cookies)
    assert inbox.json()["total"] >= 1
    assert any(
        n["notification_type"] == "event_upcoming" for n in inbox.json()["items"]
    )


@pytest.mark.asyncio
async def test_admin_scan_is_role_gated(client):
    cookies = await _login(client, email="scan-analyst@example.com", password="Hello-World-2026", role=Role.ANALYST)
    r = await client.post(
        "/admin/notifications/scan",
        cookies=cookies,
        json={"include_events": True},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_cannot_read_inbox(client):
    from httpx import ASGITransport, AsyncClient
    from apps.api.main import create_app as _create_app
    from asgi_lifespan import LifespanManager
    fresh_app = _create_app()
    fresh_transport = ASGITransport(app=fresh_app)
    async with LifespanManager(fresh_app):
        async with AsyncClient(transport=fresh_transport, base_url="http://test") as fresh:
            r = await fresh.get("/notifications")
            assert r.status_code == 401


# --- helpers ---------------------------------------------------------
def _event_candidate(org: UUID, user: UUID):
    from livelead.domain.notifications import NotificationCandidate, NotificationType, SourceRecordType
    return NotificationCandidate(
        organization_id=org,
        user_id=user,
        notification_type=NotificationType.EVENT_UPCOMING,
        source_record_type=SourceRecordType.EVENT,
        source_record_id=str(uuid4()),
        title="Acme event soon",
        summary="Acme event starts in 10 minutes.",
        deep_link=f"/events/{uuid4()}",
    )


async def _build_event_candidate(org: UUID, user: UUID, _unused: UUID):
    return [_event_candidate(org, user)]
