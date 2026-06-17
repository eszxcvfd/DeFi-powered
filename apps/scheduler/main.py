"""Scheduler process — dispatches due discovery schedules (US-035) and
pending webhook deliveries (US-049)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

from livelead.application.discovery.schedule_dispatch import dispatch_due_schedules
from livelead.runtime.settings import parse_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("livelead.scheduler")


async def _dispatch_pending_webhooks() -> int:
    """Run the bounded webhook dispatcher for
    every `pending` and `failed` delivery
    whose `next_attempt_at` has elapsed.

    The bounded path uses the same
    `AsyncSession` factory the rest of the
    product uses; the actor returns the
    number of dispatched deliveries.
    """

    from livelead.infrastructure.db.session import (
        create_engine,
        create_session_factory,
    )
    from livelead.infrastructure.secrets.vault import SecretVault
    from livelead.application.webhooks import (
        WebhookDeliveryService,
    )
    from livelead.domain.webhooks.models import (
        WebhookDeliveryThresholds,
    )

    settings = parse_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    vault = SecretVault(settings.secret_master_key)

    async with factory() as session:
        service = WebhookDeliveryService(
            session,
            vault=vault,
            environment_mode=settings.environment_mode,
            thresholds=WebhookDeliveryThresholds(),
        )
        try:
            results = await service.dispatch_pending()
        except Exception:  # noqa: BLE001
            logger.exception(
                "webhook.dispatch_pending failed"
            )
            return 0
        try:
            await session.commit()
        except Exception:  # noqa: BLE001
            logger.exception(
                "webhook.dispatch_pending commit failed"
            )
            await session.rollback()
            return 0
    try:
        engine.sync_engine.dispose()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        try:
            engine.dispose()
        except Exception:  # noqa: BLE001
            pass
    return len(results)


def run_once() -> int:
    settings = parse_settings()
    logger.info(
        "scheduler tick environment=%s sqlite=%s redis=%s",
        settings.environment,
        settings.sqlite_path,
        settings.redis_url,
    )
    results = dispatch_due_schedules(enqueue=True)
    logger.info("scheduler tick complete dispatched=%s", len(results))
    for item in results:
        logger.info("schedule_dispatch_result %s", item)
    webhook_dispatched = asyncio.run(_dispatch_pending_webhooks())
    logger.info(
        "webhook dispatch tick complete dispatched=%s",
        webhook_dispatched,
    )
    return 0


def run_loop(interval_sec: float) -> int:
    logger.info("scheduler loop interval_sec=%s", interval_sec)
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("scheduler tick failed")
        time.sleep(interval_sec)


def main() -> int:
    mode = os.environ.get("LIVELEAD_SCHEDULER_MODE", "once").lower()
    if mode == "loop":
        interval = float(os.environ.get("LIVELEAD_SCHEDULER_INTERVAL_SEC", "60"))
        return run_loop(interval)
    return run_once()


if __name__ == "__main__":
    sys.exit(main())
