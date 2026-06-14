from livelead.domain.browser.models import BrowserEngine
from livelead.infrastructure.browser.chromium_path import resolve_chromium_executable
from livelead.runtime.settings import AppSettings


def test_resolve_uses_livelead_playwright_env(monkeypatch):
    monkeypatch.delenv("LIVELEAD_PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    monkeypatch.setenv("LIVELEAD_PLAYWRIGHT_CHROMIUM_EXECUTABLE", "/usr/bin/google-chrome-stable")
    s = AppSettings(playwright_chromium_executable=None)
    assert (
        resolve_chromium_executable(s, BrowserEngine.PLAYWRIGHT) == "/usr/bin/google-chrome-stable"
    )
