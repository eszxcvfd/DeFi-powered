"""Scheduler process bootstrap — no cron jobs in Foundation."""

import logging
import sys

from livelead.runtime.settings import parse_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("livelead.scheduler")


def main() -> int:
    settings = parse_settings()
    logger.info(
        "scheduler ready environment=%s sqlite=%s redis=%s",
        settings.environment,
        settings.sqlite_path,
        settings.redis_url,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
