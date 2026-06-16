"""Foundation worker tasks (US-001, US-040, US-041)."""

# Register all domain tasks
import apps.worker.alert_tasks as _  # noqa: F401
import apps.worker.discovery_tasks as _  # noqa: F401
import dramatiq

from livelead.infrastructure.db.session import create_engine, create_session_factory
from livelead.infrastructure.observability.worker_heartbeat import (
    make_dramatiq_middleware,
)
from livelead.infrastructure.queue.broker import configure_broker
from livelead.runtime.settings import parse_settings

_settings = parse_settings()
configure_broker(_settings)
_engine = create_engine(_settings)
_session_factory = create_session_factory(_engine)


@dramatiq.actor(queue_name="default")
def smoke_ping(message: str = "ping") -> str:
    return f"ok:{message}"


@dramatiq.actor(queue_name="default")
def record_worker_heartbeat(task: str = "manual") -> str:
    """Record a worker heartbeat. Useful for ops scripts and tests."""
    from livelead.infrastructure.observability.worker_heartbeat import (
        record_heartbeat_async,
    )
    import asyncio

    asyncio.run(
        record_heartbeat_async(_session_factory, last_task=task)
    )
    return "recorded"


# Register the heartbeat middleware so the launch gate can detect a
# live worker whenever tasks are being processed.
dramatiq.get_broker().add_middleware(make_dramatiq_middleware(_session_factory))
