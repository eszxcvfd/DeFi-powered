"""Browser worker bootstrap — Playwright sessions run in API process threads; worker validates runtime."""

import logging
import sys

from livelead.infrastructure.browser.factory import get_browser_runtime
from livelead.runtime.settings import parse_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("livelead.browser_worker")


def main() -> int:
    settings = parse_settings()
    mode = settings.browser_automation_mode
    if mode == "stub":
        logger.warning("browser_worker LIVELEAD_BROWSER_AUTOMATION=stub — no real Chromium sessions")
    elif mode != "playwright":
        logger.info("browser_worker automation_mode=%s (maps to Playwright runtime)", mode)
    else:
        try:
            import playwright  # noqa: F401
        except ImportError:
            logger.error(
                "playwright not installed; pip install 'livelead[browser]' && playwright install chromium"
            )
            return 1
    _ = get_browser_runtime()
    logger.info(
        "browser_worker ready environment=%s automation=%s headless=%s",
        settings.environment,
        mode,
        settings.browser_headless,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())