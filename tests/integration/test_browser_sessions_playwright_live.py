"""Live Playwright navigation — skipped unless LIVELEAD_BROWSER_LIVE_TEST=1."""

import asyncio
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LIVELEAD_BROWSER_LIVE_TEST") != "1",
    reason="set LIVELEAD_BROWSER_LIVE_TEST=1 to run real Chromium sessions",
)


@pytest.fixture
def live_browser_env(monkeypatch):
    monkeypatch.setenv("LIVELEAD_BROWSER_AUTOMATION_MODE", "playwright")
    from livelead.infrastructure.browser.factory import reset_runtime_cache_for_tests

    reset_runtime_cache_for_tests()
    yield
    reset_runtime_cache_for_tests()


@pytest.mark.asyncio
async def test_real_playwright_loads_example_com(client, live_browser_env):
    try:
        import playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright not installed")

    src = await client.post(
        "/admin/connectors",
        headers={"X-Actor-Role": "admin"},
        json={
            "name": "Live PW",
            "domain": "example.com",
            "connector_type": "browser",
            "automation_engine": "playwright",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    assert src.status_code == 201
    sid = src.json()["id"]
    create = await client.post(
        "/browser-sessions",
        json={"source_id": sid, "initial_url": "https://example.com/"},
    )
    assert create.status_code == 201
    session_id = create.json()["id"]

    for _ in range(60):
        st = await client.get(f"/browser-sessions/{session_id}")
        state = st.json()["state"]
        if state in ("running", "failed", "stopped"):
            break
        await asyncio.sleep(0.25)

    body = (await client.get(f"/browser-sessions/{session_id}")).json()
    assert body["state"] == "running", body
    assert "example.com" in body["current_url"]

    stop = await client.post(f"/browser-sessions/{session_id}/stop")
    assert stop.status_code == 200
    assert stop.json()["state"] == "stopped"
