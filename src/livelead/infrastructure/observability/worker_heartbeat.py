"""Worker heartbeat recorder (US-040).

The Dramatiq worker calls `record_heartbeat` whenever it finishes a
task. The launch gate reads the latest row from `worker_heartbeats`
to verify the worker is alive before allowing `pilot_live` entry.

The function is intentionally synchronous-friendly: it builds its own
asyncio loop or uses the running one to insert a row. Tests and
verify scripts may also call it directly to seed a heartbeat before
checking the launch gate.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import datetime
from typing import Any

logger = logging.getLogger("livelead.worker_heartbeat")

_DEFAULT_WORKER_ID = "livelead-worker"


def current_worker_id() -> str:
    """Return the worker id used by this process.

    Operators may override the id with the `LIVELEAD_WORKER_ID` env
    var so multi-worker deployments distinguish their heartbeats.
    """

    return os.environ.get("LIVELEAD_WORKER_ID") or _DEFAULT_WORKER_ID


async def record_heartbeat_async(
    session_factory,
    *,
    worker_id: str | None = None,
    last_task: str = "",
    detail: str = "",
    organization_id: str = "",
) -> None:
    """Insert a heartbeat row using the provided async session factory."""
    from livelead.infrastructure.db.repositories.runtime import (
        WorkerHeartbeatRepository,
    )

    wid = worker_id or current_worker_id()
    async with session_factory() as session:
        await WorkerHeartbeatRepository(session).record(
            worker_id=wid,
            last_task=last_task or "",
            detail=detail or "",
            organization_id=organization_id or "",
        )
        await session.commit()


def record_heartbeat(
    session_factory,
    *,
    worker_id: str | None = None,
    last_task: str = "",
    detail: str = "",
    organization_id: str = "",
) -> None:
    """Synchronous entry point — runs the async recorder.

    Worker code that is itself inside a running loop should call
    `record_heartbeat_async` instead. The synchronous wrapper falls
    back to a dedicated event loop only when no loop is running.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(
            record_heartbeat_async(
                session_factory,
                worker_id=worker_id,
                last_task=last_task,
                detail=detail,
                organization_id=organization_id,
            )
        )
        return

    if loop.is_running():
        # We're already inside a running loop (e.g. a Dramatiq worker
        # thread that started its own event loop). Schedule the
        # coroutine and wait for completion.
        future = asyncio.run_coroutine_threadsafe(
            record_heartbeat_async(
                session_factory,
                worker_id=worker_id,
                last_task=last_task,
                detail=detail,
                organization_id=organization_id,
            ),
            loop,
        )
        future.result(timeout=10)
        return

    loop.run_until_complete(
        record_heartbeat_async(
            session_factory,
            worker_id=worker_id,
            last_task=last_task,
            detail=detail,
            organization_id=organization_id,
        )
    )


def make_dramatiq_middleware(session_factory):
    """Return a Dramatiq middleware that records a heartbeat per message.

    Operators wire it via `dramatiq.broker.add_middleware`. The
    middleware records a heartbeat both before and after a message is
    processed so the launch gate always has a recent row whenever the
    worker is alive and serving tasks.
    """

    from dramatiq import Middleware

    class HeartbeatMiddleware(Middleware):
        def before_process_message(self, broker, message):
            try:
                record_heartbeat(
                    session_factory,
                    last_task=message.actor_name or "",
                    detail=(message.message_id or "")[:64],
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("heartbeat_before_failed: %s", exc)

        def after_process_message(self, broker, message, *, result=None, exception=None):
            try:
                record_heartbeat(
                    session_factory,
                    last_task=message.actor_name or "",
                    detail=(message.message_id or "")[:64],
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("heartbeat_after_failed: %s", exc)

    return HeartbeatMiddleware()
