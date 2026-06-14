"""Configure Dramatiq Redis broker from settings."""

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from livelead.runtime.settings import AppSettings

_broker = None


def configure_broker(settings: AppSettings) -> RedisBroker:
    global _broker
    if _broker is None:
        _broker = RedisBroker(url=settings.redis_url)
        dramatiq.set_broker(_broker)
    return _broker


def ping_redis(settings: AppSettings) -> bool:
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        return bool(client.ping())
    except Exception:
        return False
