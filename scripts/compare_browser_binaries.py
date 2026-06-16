#!/usr/bin/env python3
"""Compare CloakBrowser vs Chrome for LiveLead (informational)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from livelead.domain.browser.models import BrowserEngine
from livelead.infrastructure.browser.chromium_path import (
    require_chromium_executable,
    resolve_chromium_executable,
)
from livelead.runtime.settings import parse_settings

BINARIES = [
    ("cloakbrowser", "/usr/local/bin/cloakbrowser"),
    ("google-chrome", "/usr/bin/google-chrome-stable"),
]


def main() -> int:
    s = parse_settings()
    print("== LiveLead binary resolution ==")
    print("  cloakbrowser engine ->", require_chromium_executable(s, BrowserEngine.CLOAKBROWSER))
    print("  playwright engine   ->", resolve_chromium_executable(s, BrowserEngine.PLAYWRIGHT))
    print()
    print("== Playwright smoke (headless) ==")
    from playwright.sync_api import sync_playwright

    for name, exe in BINARIES:
        t0 = time.perf_counter()
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True, executable_path=exe)
                page = b.new_page()
                page.goto("https://example.com", timeout=30_000, wait_until="domcontentloaded")
                title = page.title()
                b.close()
            print(f"  {name}: OK {(time.perf_counter() - t0) * 1000:.0f}ms title={title!r}")
        except Exception as exc:
            print(f"  {name}: FAIL {exc}")

    print()
    print("Note: LiveLead uses cloakbrowser binary only when connector automation_engine=cloakbrowser")
    print("      and US-025 policy is approved. Default playwright engine uses Chrome path above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())