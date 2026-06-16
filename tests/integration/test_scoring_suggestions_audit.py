"""US-039 audit emission for scoring suggestions."""

import pytest

from livelead.domain.audit.enums import AuditAction

ADMIN = {"X-Actor-Role": "admin", "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_generate_and_approve_emit_scoring_suggestion_audit(client):
    camp = await client.post(
        "/campaigns",
        json={"name": "US039 Audit", "target_industry": "Tech", "positive_keywords": ["summit"]},
    )
    cid = camp.json()["id"]
    for _ in range(2):
        resp = await client.post(
            f"/campaigns/{cid}/discovery-copilot:respond",
            headers=ADMIN,
            json={"question": "What discovery keywords fit this tech summit campaign?"},
        )
        rid = resp.json()["id"]
        await client.put(
            f"/discovery-copilot-responses/{rid}/feedback",
            headers=ADMIN,
            json={"state": "not_helpful", "reason_code": "weak_usefulness"},
        )

    gen = await client.post(f"/campaigns/{cid}/scoring-suggestions:generate", headers=ADMIN)
    assert gen.status_code == 201
    sid = gen.json()["id"]

    listed = await client.get(
        "/admin/audit-logs",
        headers=ADMIN,
        params={"action": AuditAction.SCORING_SUGGESTION_GENERATED.value, "limit": 20},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    approve = await client.post(
        f"/campaigns/{cid}/scoring-suggestions/{sid}:approve",
        headers=ADMIN,
    )
    assert approve.status_code == 200

    listed2 = await client.get(
        "/admin/audit-logs",
        headers=ADMIN,
        params={"action": AuditAction.SCORING_SUGGESTION_APPROVED.value, "limit": 20},
    )
    assert listed2.status_code == 200
    assert listed2.json()["total"] >= 1