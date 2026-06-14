import pytest

from livelead.application.queries.health import get_health_status
from livelead.runtime.settings import AppSettings


@pytest.mark.asyncio
async def test_health_query_smoke_handler():
    settings = AppSettings(environment="test")
    status = await get_health_status(settings, sqlite_ok=True, redis_ok=False)
    assert status.service == "livelead-api"
    assert status.status == "ok"
    assert len(status.components) == 2
