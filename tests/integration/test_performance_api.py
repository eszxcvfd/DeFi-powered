"""Integration tests for the performance baseline and SLO admin API (US-044)."""

from __future__ import annotations

import pytest


def _owner_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "owner",
    }


def _analyst_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "analyst",
    }


def _viewer_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "viewer",
    }


@pytest.mark.asyncio
async def test_performance_summary_forbidden_for_analyst(migrated_client):
    r = await migrated_client.get(
        "/admin/performance/summary",
        headers=_analyst_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_performance_summary_forbidden_for_viewer(migrated_client):
    r = await migrated_client.get(
        "/admin/performance/summary",
        headers=_viewer_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_performance_summary_returns_empty_entries(migrated_client):
    r = await migrated_client.get(
        "/admin/performance/summary",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    assert len(body["entries"]) == 5
    # Each entry is present with a None snapshot and
    # the documented budget and metric.
    scenarios = {e["scenario"] for e in body["entries"]}
    assert scenarios == {
        "api_read_latency",
        "event_list_pagination",
        "discovery_first_progress",
        "concurrency_cap",
        "browser_session_budget",
    }
    for entry in body["entries"]:
        assert entry["snapshot"] is None
        assert entry["breach"] is False


@pytest.mark.asyncio
async def test_list_performance_snapshots_empty(migrated_client):
    r = await migrated_client.get(
        "/admin/performance/snapshots",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_run_scenario_records_snapshot(migrated_client):
    r = await migrated_client.post(
        "/admin/performance/scenarios:run",
        json={"scenario": "api_read_latency"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario"] == "api_read_latency"
    assert body["p50_ms"] >= 0
    assert body["p95_ms"] >= 0
    assert body["p99_ms"] >= 0
    assert body["rps"] >= 0


@pytest.mark.asyncio
async def test_run_scenario_rejects_unknown_scenario(migrated_client):
    r = await migrated_client.post(
        "/admin/performance/scenarios:run",
        json={"scenario": "not_a_scenario"},
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "PERFORMANCE_INVALID" in r.json()["detail"]


@pytest.mark.asyncio
async def test_run_scenario_forbidden_for_analyst(migrated_client):
    r = await migrated_client.post(
        "/admin/performance/scenarios:run",
        json={"scenario": "api_read_latency"},
        headers=_analyst_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_run_scenario_forbidden_for_viewer(migrated_client):
    r = await migrated_client.post(
        "/admin/performance/scenarios:run",
        json={"scenario": "api_read_latency"},
        headers=_viewer_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_performance_snapshots_after_run(migrated_client):
    # Run a scenario to produce a snapshot.
    r1 = await migrated_client.post(
        "/admin/performance/scenarios:run",
        json={"scenario": "event_list_pagination"},
        headers=_owner_headers(),
    )
    assert r1.status_code == 200
    # List snapshots, filtered to the scenario.
    r2 = await migrated_client.get(
        "/admin/performance/snapshots?scenario=event_list_pagination",
        headers=_owner_headers(),
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] >= 1
    assert all(
        item["scenario"] == "event_list_pagination" for item in body["items"]
    )


@pytest.mark.asyncio
async def test_performance_summary_after_run_no_breach(migrated_client):
    # The bounded harness runs within the SLO budget;
    # the summary entry must report breach=False.
    await migrated_client.post(
        "/admin/performance/scenarios:run",
        json={"scenario": "api_read_latency"},
        headers=_owner_headers(),
    )
    r = await migrated_client.get(
        "/admin/performance/summary",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    entry = next(
        e for e in body["entries"] if e["scenario"] == "api_read_latency"
    )
    assert entry["snapshot"] is not None
    assert entry["breach"] is False
