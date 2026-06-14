import pytest

PAYLOAD = {
    "name": "Manual child",
    "description": "",
    "target_industry": "X",
    "product_or_service_focus": "",
    "market_regions": [],
    "languages": [],
    "timezone": "UTC",
    "date_range": {"start": None, "end": None},
    "positive_keywords": [],
    "exclude_keywords": [],
    "icp": {
        "industry": "",
        "organization_type": "",
        "company_size": "",
        "role_or_title_targets": [],
        "country_or_region": "",
        "pain_points": [],
        "use_cases": [],
        "positive_keywords": [],
        "excluded_keywords": [],
    },
    "scoring_weights": {},
}


@pytest.mark.asyncio
async def test_playwright_campaign_gets_parent(client):
    create = await client.post(
        "/campaigns",
        json={**PAYLOAD, "name": "PW Child"},
        headers={
            "X-Creation-Source": "playwright",
            "X-Actor-Label": "e2e-runner",
            "X-Automation-Run-Id": "test-run-1",
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["parent_campaign_id"] is not None
    assert body["creation_source"] == "playwright"
    assert body["created_by_actor"] == "e2e-runner"
    assert body["parent_name"]

    listed = await client.get("/campaigns")
    assert listed.status_code == 200
    items = listed.json()
    root = next(i for i in items if i["creation_source"] == "automation_root")
    assert root["child_count"] >= 1
    child = next(i for i in items if i["name"] == "PW Child")
    assert child["depth"] == 1