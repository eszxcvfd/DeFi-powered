import logging

import pytest


@pytest.mark.asyncio
async def test_health_request_emits_structured_log(client, caplog):
    caplog.set_level(logging.INFO, logger="livelead.request")
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("x-request-id")
    assert any("GET /health" in rec.message for rec in caplog.records)