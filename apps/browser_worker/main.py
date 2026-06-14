"""Browser worker bootstrap — no live third-party automation in Foundation."""

import logging
import sys

from livelead.runtime.settings import parse_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("livelead.browser_worker")


def main() -> int:
    settings = parse_settings()
    logger.info(
        "browser_worker ready environment=%s policy=stub_no_external_targets",
        settings.environment,
    )
    _ = settings.redis_url
    return 0


if __name__ == "__main__":
    sys.exit(main())