"""Foundation worker tasks."""

# Register all domain tasks
import apps.worker.discovery_tasks as _  # noqa: F401
import dramatiq

from livelead.infrastructure.queue.broker import configure_broker
from livelead.runtime.settings import parse_settings

_settings = parse_settings()
configure_broker(_settings)


@dramatiq.actor(queue_name="default")
def smoke_ping(message: str = "ping") -> str:
    return f"ok:{message}"