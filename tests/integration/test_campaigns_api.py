import pytest

PAYLOAD = {
    "name": "Payments EU",
    "description": "Find webinars",
    "target_industry": "Fintech",
    "product_or_service_focus": "Cross-border payments",
    "market_regions": ["EU"],
    "languages": ["en"],
    "timezone": "Europe/Berlin",
    "date_range": {"start": "2026-07-01", "end": "2026-12-31"},
    "positive_keywords": ["webinar"],
    "exclude_keywords": ["crypto scam"],
    "icp": {
        "industry": "Payments",
        "organization_type": "SaaS",
        "company_size": "50-200",
        "role_or_title_targets": ["Head of Partnerships"],
        "country_or_region": "EU",
        "pain_points": ["compliance"],
        "use_cases": ["lead gen"],
        "positive_keywords": ["B2B"],
        "excluded_keywords": [],
    },
    "scoring_weights": {"topic_relevance": 0.3, "icp_match": 0.3},
}


@pytest.mark.asyncio
async def test_campaign_crud_scoped_to_organization(client):
    other_org = "00000000-0000-4000-8000-000000000099"
    create = await client.post("/campaigns", json=PAYLOAD)
    assert create.status_code == 201
    body = create.json()
    cid = body["id"]
    assert body["target_industry"] == "Fintech"
    assert body["icp"]["industry"] == "Payments"
    assert "topic_relevance" in body["scoring_weights"]
    assert body["deferred"]["run_discovery"] == "enabled"

    listed = await client.get("/campaigns")
    assert listed.status_code == 200
    assert any(c["id"] == cid for c in listed.json())

    detail = await client.get(f"/campaigns/{cid}")
    assert detail.status_code == 200

    patch = await client.patch(f"/campaigns/{cid}", json={"name": "Payments EU v2"})
    assert patch.status_code == 200
    assert patch.json()["name"] == "Payments EU v2"

    forbidden = await client.get(
        f"/campaigns/{cid}",
        headers={"X-Organization-Id": other_org},
    )
    assert forbidden.status_code == 404