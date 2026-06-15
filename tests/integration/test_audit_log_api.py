"""Audit-log API integration (US-026)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest


ADMIN = {"X-Actor-Role": "admin"}
ANALYST = {"X-Actor-Role": "analyst"}
COMPLIANCE = {"X-Actor-Role": "compliance"}


async def _cloak_source(client) -> str:
    r = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": f"Audit Cloak {uuid4().hex[:6]}",
            "domain": f"audit-{uuid4().hex[:6]}.example.com",
            "connector_type": "browser",
            "automation_engine": "cloakbrowser",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_audit_log_captures_cloakbrowser_workflow_and_role_gates_reads(client):
    sid = await _cloak_source(client)
    rid = f"req-{uuid4().hex[:8]}"
    headers = {**ADMIN, "x-request-id": rid}

    req = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/request",
        headers=headers,
        json={"purpose_rationale": "audit capture", "pinned_version": "1.0.0"},
    )
    assert req.status_code == 200

    oa = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/approve-owner-admin", headers=headers
    )
    assert oa.status_code == 200

    comp = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/approve-compliance",
        headers={**COMPLIANCE, "x-request-id": rid},
    )
    assert comp.status_code == 200

    # Filter by request_id so we only see the workflow we just emitted.
    listed = await client.get(
        "/admin/audit-logs",
        headers=ADMIN,
        params={"request_id": rid, "limit": 50},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 3
    actions = {item["action"] for item in body["items"]}
    assert "cloakbrowser.policy.requested" in actions
    assert "cloakbrowser.policy.owner_approved" in actions
    assert "cloakbrowser.policy.compliance_approved" in actions
    for item in body["items"]:
        assert item["context"].get("request_id") == rid
        assert item["actor"]["role"] in {"admin", "compliance"}
        assert item["actor"]["actor_type"] == "human"

    # Non-admin cannot read.
    denied = await client.get("/admin/audit-logs", headers=ANALYST)
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_entry_detail_and_cross_tenant_isolation(client):
    sid = await _cloak_source(client)
    rid = f"req-detail-{uuid4().hex[:8]}"
    await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/request",
        headers={**ADMIN, "x-request-id": rid},
        json={"purpose_rationale": "detail scope"},
    )

    listed = await client.get(
        "/admin/audit-logs",
        headers=ADMIN,
        params={"request_id": rid, "limit": 5},
    )
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items, "expected at least one audit row for this workflow"
    entry_id = items[0]["id"]

    detail = await client.get(f"/admin/audit-logs/{entry_id}", headers=ADMIN)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["id"] == entry_id
    assert detail_body["context"].get("request_id") == rid
    assert detail_body["organization_id"]

    # Cross-tenant read must return 404 (tenant isolation).
    other_org = "11111111-1111-4111-8111-111111111111"
    cross = await client.get(
        f"/admin/audit-logs/{entry_id}",
        headers={**ADMIN, "X-Organization-Id": other_org},
    )
    assert cross.status_code == 404


@pytest.mark.asyncio
async def test_audit_log_redacts_secret_metadata(client):
    """A redaction fixture proves secret-like metadata is collapsed before persistence."""

    from livelead.domain.audit.model import (
        AuditActor,
        AuditContext,
        AuditTarget,
        normalize_entry,
    )
    from livelead.domain.audit.enums import (
        AuditAction,
        AuditActorType,
        AuditOutcome,
        AuditTargetType,
    )
    from livelead.domain.audit.redaction import REDACTED
    from livelead.application.audit.audit_service import AuditService

    from livelead.infrastructure.db.repositories.audit_log import AuditEntryRepository

    org = uuid4()
    factory = client.app.state.session_factory
    async with factory() as sess:
        entry = normalize_entry(
            organization_id=org,
            actor=AuditActor(actor_id="admin", actor_type=AuditActorType.HUMAN, role="admin"),
            action=AuditAction.SOURCE_POLICY_CHANGED,
            target=AuditTarget(
                target_type=AuditTargetType.SOURCE, target_id="src-x", display="src-x"
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=AuditContext(request_id="req-redact"),
            metadata={
                "api_key": "sk-test-1234567890ABCDEF",
                "token": "plain-text-secret",
                "note": "harmless",
            },
        )
        await AuditService(sess).emit(
            organization_id=org,
            actor=AuditActor(actor_id="admin", actor_type=AuditActorType.HUMAN, role="admin"),
            action=AuditAction.SOURCE_POLICY_CHANGED,
            target=AuditTarget(
                target_type=AuditTargetType.SOURCE, target_id="src-x", display="src-x"
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=AuditContext(request_id="req-redact"),
            metadata={
                "api_key": "sk-test-1234567890ABCDEF",
                "token": "plain-text-secret",
                "note": "harmless",
            },
        )
        await sess.commit()
        # Read back the row and assert the secret fields are gone.
        repo = AuditEntryRepository(sess)
        rows, total = await repo.list_for_org(org, limit=1, offset=0)
        assert total == 1
        row = rows[0]
        meta = json.loads(row.metadata_json)
        assert meta["api_key"] == REDACTED
        assert meta["token"] == REDACTED
        assert meta["note"] == "harmless"
        assert row.metadata_redacted is True
        # The domain entry is also redacted.
        assert entry.metadata["api_key"] == REDACTED


@pytest.mark.asyncio
async def test_audit_log_filter_options_endpoint(client):
    opts = await client.get("/admin/audit-logs/filters", headers=ADMIN)
    assert opts.status_code == 200
    body = opts.json()
    assert "human" in body["actor_types"]
    assert "succeeded" in body["outcomes"]
    assert "denied" in body["outcomes"]
    assert "cloakbrowser" in body["action_families"]
    assert "content" in body["action_families"]
    assert "source" in body["target_types"]
    assert "content_draft" in body["target_types"]
