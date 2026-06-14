"""Resolve Chromium/Chrome binary — avoids broken ms-playwright cache on Linux."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from livelead.domain.browser.models import BrowserEngine
from livelead.runtime.settings import AppSettings


def _is_executable(path: str | None) -> bool:
    return bool(path) and Path(path).is_file() and os.access(path, os.X_OK)


def _detect_system_chromium() -> str | None:
    for name in (
        "google-chrome-stable",
        "google-chrome",
        "chromium-browser",
        "chromium",
        "microsoft-edge-stable",
    ):
        found = shutil.which(name)
        if _is_executable(found):
            return found
    for path in (
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium",
    ):
        if _is_executable(path):
            return path
    return None


def resolve_chromium_executable(settings: AppSettings, engine: BrowserEngine) -> str | None:
    """Return executable_path for Playwright chromium.launch, or None (bundled — often missing)."""

    if engine == BrowserEngine.CLOAKBROWSER:
        for candidate in (
            settings.cloakbrowser_executable,
            os.environ.get("LIVELEAD_CLOAKBROWSER_EXECUTABLE"),
            os.environ.get("CLOAKBROWSER_EXECUTABLE"),
            "/usr/local/bin/cloakbrowser",
        ):
            if _is_executable(candidate):
                return candidate

    for candidate in (
        settings.playwright_chromium_executable,
        os.environ.get("LIVELEAD_PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
    ):
        if _is_executable(candidate):
            return candidate

    return _detect_system_chromium()


def require_chromium_executable(settings: AppSettings, engine: BrowserEngine) -> str:
    exe = resolve_chromium_executable(settings, engine)
    if exe:
        return exe
    raise RuntimeError(
        "No Chromium/Chrome binary found. Fix one of:\n"
        "  1) Run: ./scripts/playwright-install.sh\n"
        "  2) Repo root .env: LIVELEAD_PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome-stable\n"
        "  3) Or: playwright install chromium\n"
        f"(engine={engine.value})"
    )
