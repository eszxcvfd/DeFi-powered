"""US-034: Selenium browser discovery job path and canonical event ingestion."""

import pytest

from livelead.application.discovery.service import run_discovery_job

ADMIN = {"X-Actor-Role": "admin"}

_RECIPE = {
    "browser_discovery_recipe": {
        "start_url": "http://127.0.0.1:8000/dev/e2e-discovery-website",
        "item_selector": ".event-card",
        "title_selector": ".event-title",
        "link_selector": ".event-link",
        "description_selector": ".event-desc",
        "wait_for_selector": ".event-list",
        "max_items": 5,
        "time_budget_ms": 30_000,
    }
}

_FIXTURE_HTML = """<!DOCTYPE html>
<html><body>
<ul class="event-list">
  <li class="event-card">
    <a class="event-link" href="https://fixture.local/e/1"><span class="event-title">US034 Live Selenium Summit</span></a>
    <p class="event-desc">webinar payments summit</p>
  </li>
</ul>
</body></html>"""


@pytest.mark.asyncio
async def test_selenium_mock_discovery_persists_canonical_events(client, monkeypatch):
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "true")

    create_src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US034 Mock Selenium",
            "domain": "selenium-website-mock.example.com",
            "connector_type": "browser",
            "automation_engine": "selenium",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    assert create_src.status_code == 201
    src_id = create_src.json()["id"]
    await client.patch(
        f"/admin/connectors/{src_id}",
        headers=ADMIN,
        json={"rate_limit_json": _RECIPE},
    )

    camp = await client.post(
        "/campaigns",
        json={
            "name": "US034 Camp",
            "target_industry": "Fintech",
            "positive_keywords": ["summit"],
            "exclude_keywords": [],
        },
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    job = await client.post(f"/campaigns/{cid}/discovery-jobs")
    job_id = job.json()["id"]
    run_discovery_job(job_id)

    detail = await client.get(f"/discovery-jobs/{job_id}")
    body = detail.json()
    src_prog = body["progress"]["sources"][src_id]
    assert src_prog["execution_mode"] == "mock"
    assert src_prog["connector_family"] == "selenium_website"
    assert src_prog["status"] == "succeeded"

    events = await client.get(f"/campaigns/{cid}/events", params={"include_score": "false"})
    titles = [e["canonical_title"] for e in events.json()]
    assert any("US034 Selenium Summit" in t for t in titles)


@pytest.mark.asyncio
async def test_selenium_recipe_not_ready_blocks_run(client, monkeypatch):
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "false")

    create_src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US034 Incomplete",
            "domain": "incomplete-selenium.test",
            "connector_type": "browser",
            "automation_engine": "selenium",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    src_id = create_src.json()["id"]
    camp = await client.post("/campaigns", json={"name": "US034 Deny", "positive_keywords": []})
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})
    job_id = (await client.post(f"/campaigns/{cid}/discovery-jobs")).json()["id"]
    run_discovery_job(job_id)

    detail = (await client.get(f"/discovery-jobs/{job_id}")).json()
    prog = detail["progress"]["sources"][src_id]
    assert prog["status"] == "failed"
    assert "recipe_not_ready" in (prog.get("error") or "")


@pytest.mark.asyncio
async def test_live_selenium_file_fixture_extraction(client, monkeypatch, tmp_path):
    try:
        import selenium  # noqa: F401
    except ImportError:
        pytest.skip("selenium not installed")

    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "false")

    html_path = tmp_path / "events.html"
    html_path.write_text(_FIXTURE_HTML, encoding="utf-8")
    start_url = html_path.as_uri()

    create_src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US034 Live Fixture",
            "domain": "fixture-selenium.local",
            "connector_type": "browser",
            "automation_engine": "selenium",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    src_id = create_src.json()["id"]
    await client.patch(
        f"/admin/connectors/{src_id}",
        headers=ADMIN,
        json={
            "rate_limit_json": {
                "browser_discovery_recipe": {
                    "start_url": start_url,
                    "item_selector": ".event-card",
                    "title_selector": ".event-title",
                    "link_selector": "a.event-link",
                    "description_selector": ".event-desc",
                    "wait_for_selector": ".event-list",
                    "max_items": 5,
                    "time_budget_ms": 45_000,
                }
            }
        },
    )

    camp = await client.post(
        "/campaigns",
        json={"name": "US034 Live", "positive_keywords": ["Selenium"]},
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})
    job_id = (await client.post(f"/campaigns/{cid}/discovery-jobs")).json()["id"]

    run_discovery_job(job_id)

    detail = await client.get(f"/discovery-jobs/{job_id}")
    prog = detail.json()["progress"]["sources"][src_id]
    err = (prog.get("error") or "").lower()
    if prog["status"] == "failed" and (
        "chromium" in err or "chrome" in err or "selenium" in err or "executable" in err
    ):
        pytest.skip("chromium not available for live selenium discovery")
    assert prog["execution_mode"] == "selenium_website"
    assert prog["status"] == "succeeded", prog.get("error")
    assert prog["items_found"] >= 1

    events = await client.get(f"/campaigns/{cid}/events", params={"include_score": "false"})
    titles = [e["canonical_title"] for e in events.json()]
    assert any("US034 Live Selenium Summit" in t for t in titles)