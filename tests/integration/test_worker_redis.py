import pytest

from livelead.infrastructure.queue.broker import configure_broker, ping_redis
from livelead.runtime.settings import parse_settings


@pytest.mark.asyncio
async def test_redis_ping_when_available(monkeypatch):
    monkeypatch.setenv("LIVELEAD_REDIS_URL", "redis://127.0.0.1:6379/0")
    settings = parse_settings()
    if not ping_redis(settings):
        pytest.skip("Redis not running — start with docker compose up -d redis")
    configure_broker(settings)
    import dramatiq

    assert dramatiq.get_broker() is not None