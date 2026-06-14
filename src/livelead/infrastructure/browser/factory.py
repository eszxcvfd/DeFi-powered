"""Select browser session runtime from settings."""

from __future__ import annotations

from functools import lru_cache

from livelead.infrastructure.browser.playwright_runtime import PlaywrightBrowserRuntime
from livelead.infrastructure.browser.runtime_protocol import BrowserSessionRuntime
from livelead.infrastructure.browser.stub_runtime import StubBrowserRuntime
from livelead.runtime.settings import parse_settings


@lru_cache(maxsize=1)
def get_browser_runtime() -> BrowserSessionRuntime:
    mode = parse_settings().browser_automation_mode.lower().strip()
    if mode == "stub":
        return StubBrowserRuntime()
    if mode in ("playwright", "cloakbrowser", "real", "live"):
        return PlaywrightBrowserRuntime()
    return PlaywrightBrowserRuntime()


def reset_runtime_cache_for_tests() -> None:
    get_browser_runtime.cache_clear()
