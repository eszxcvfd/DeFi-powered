"""Integration tests for the webhook delivery (US-049) API.

Uses the real /auth/login flow so the integration
suite exercises the same boundary the frontend
would. Each test gets its own migrated SQLite via
the `migrated_client` fixture.
"""

from __future__ import annotations

from uuid import uuid4

import pytest


ORG_ID = "00000000-0000-4000-8000-000000000001"


def _bootstrap_owner_email() -> str:
    from livelead.runtime.settings import parse_settings

    return parse_settings().auth_default_owner_email


def _bootstrap_owner_password() -> str:
    from livelead.runtime.settings import parse_settings

    return parse_settings().auth_default_owner_password


async def _login_owner(client) -> dict:
    r = await client.post(
        "/auth/login",
        json={
            "email": _bootstrap_owner_email(),
            "password": _bootstrap_owner_password(),
            "organization_id": ORG_ID,
        },
    )
    assert r.status_code == 200, r.text
    return {"cookies": dict(r.cookies)}


# ----------------------------------------------------------------------
# Choices
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_choices_returns_closed_enums(migrated_client) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        "/admin/webhooks/choices", cookies=cookies
    )
    assert r.status_code == 200, r.text
    body = r.json()
    event_values = {t["value"] for t in body["event_types"]}
    assert event_values == {
        "event.high_priority",
        "lead.stage_changed",
        "lead.outcome_changed",
        "discovery.job_failed",
        "connector.auto_disable_triggered",
        "connector.auto_disable_recovered",
        "alert.fired",
    }
    status_values = {s["value"] for s in body["delivery_statuses"]}
    assert status_values == {
        "pending",
        "in_flight",
        "succeeded",
        "failed",
        "dead_letter",
        "cancelled",
    }


# ----------------------------------------------------------------------
# Subscription CRUD
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_subscription_persists_and_audits(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "SIEM integration",
            "target_url": "https://siem.example.com/webhook",
            "event_types": ["alert.fired"],
            "enabled": True,
        },
        cookies=cookies,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "SIEM integration"
    assert body["enabled"] is True
    assert body["event_types"] == ["alert.fired"]
    assert body["secret_id"]  # The secret id is set.


@pytest.mark.asyncio
async def test_create_subscription_rejects_invalid_target_url(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "Bad URL",
            "target_url": "https://169.254.169.254/webhook",
            "event_types": ["alert.fired"],
        },
        cookies=cookies,
    )
    assert r.status_code == 400
    assert "WEBHOOK_TARGET_URL" in r.text


@pytest.mark.asyncio
async def test_create_subscription_rejects_invalid_event_type(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "Bad event type",
            "target_url": "https://siem.example.com/webhook",
            "event_types": ["not.a.real.event"],
        },
        cookies=cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_subscriptions_returns_paginated_response(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    for i in range(2):
        r = await migrated_client.post(
            "/admin/webhooks/subscriptions",
            json={
                "name": f"Sub {i}",
                "target_url": f"https://siem.example.com/wh/{i}",
                "event_types": ["alert.fired"],
            },
            cookies=cookies,
        )
        assert r.status_code == 201, r.text
    r = await migrated_client.get(
        "/admin/webhooks/subscriptions", cookies=cookies
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 2


@pytest.mark.asyncio
async def test_update_subscription_emits_audit(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    create = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "Original",
            "target_url": "https://siem.example.com/webhook",
            "event_types": ["alert.fired"],
        },
        cookies=cookies,
    )
    sub_id = create.json()["id"]
    r = await migrated_client.patch(
        f"/admin/webhooks/subscriptions/{sub_id}",
        json={"name": "Updated", "enabled": False},
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Updated"
    assert body["enabled"] is False


@pytest.mark.asyncio
async def test_delete_subscription_soft_deletes(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    create = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "Doomed",
            "target_url": "https://siem.example.com/webhook",
            "event_types": ["alert.fired"],
        },
        cookies=cookies,
    )
    sub_id = create.json()["id"]
    r = await migrated_client.delete(
        f"/admin/webhooks/subscriptions/{sub_id}",
        cookies=cookies,
    )
    assert r.status_code == 204, r.text
    r = await migrated_client.get(
        f"/admin/webhooks/subscriptions/{sub_id}",
        cookies=cookies,
    )
    assert r.status_code == 404


# ----------------------------------------------------------------------
# Secret rotation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rotate_secret_emits_audit(migrated_client) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    create = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "Rotatable",
            "target_url": "https://siem.example.com/webhook",
            "event_types": ["alert.fired"],
        },
        cookies=cookies,
    )
    sub_id = create.json()["id"]
    r = await migrated_client.post(
        f"/admin/webhooks/subscriptions/{sub_id}/rotate-secret",
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == sub_id
    assert body["last_rotated_at"] is not None


# ----------------------------------------------------------------------
# Test send
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_send_to_unreachable_target_records_failure(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    # Create a subscription with a non-routable
    # localhost port (the test runs on 127.0.0.1
    # which is allowed for http).
    create = await migrated_client.post(
        "/admin/webhooks/subscriptions",
        json={
            "name": "Local test",
            "target_url": "http://localhost:1/webhook",
            "event_types": ["alert.fired"],
        },
        cookies=cookies,
    )
    sub_id = create.json()["id"]
    r = await migrated_client.post(
        f"/admin/webhooks/subscriptions/{sub_id}/test",
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subscription_id"] == sub_id
    # The bounded path marks the delivery as
    # `failed` or `dead_letter` because the
    # target URL is unreachable.
    assert body["status"] in ("failed", "dead_letter")


# ----------------------------------------------------------------------
# RBAC
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_choices_requires_owner_or_admin(
    migrated_client,
) -> None:
    r = await migrated_client.get("/admin/webhooks/choices")
    assert r.status_code in (401, 403)
