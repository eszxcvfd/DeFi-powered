"""Sync Playwright extraction for discovery jobs (infrastructure, US-033)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from livelead.domain.browser.navigation import (
    NavigationOutcome,
    classify_http_status,
    classify_navigation_exception,
)
from livelead.domain.discovery.browser_recipe import BrowserDiscoveryRecipe
from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.discovery.models import SourceRunStatus
from livelead.infrastructure.connectors.browser_discovery_extraction import (
    body_indicates_challenge,
    make_discovery_finding,
    resolve_item_link,
)

if TYPE_CHECKING:
    from livelead.runtime.settings import AppSettings

logger = logging.getLogger("livelead.playwright_discovery")


@dataclass(frozen=True, slots=True)
class PlaywrightDiscoveryRunOutcome:
    status: SourceRunStatus
    items_found: int
    pages_processed: int
    error_summary: str | None
    findings: tuple[DiscoveryFinding, ...]


def _detect_challenge(page: object, recipe: BrowserDiscoveryRecipe) -> bool:
    for sel in recipe.challenge_selectors:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    try:
        body = (page.locator("body").inner_text(timeout=2000) or "").lower()
    except Exception:
        body = ""
    return body_indicates_challenge(body)


def _extract_findings(page: object, recipe: BrowserDiscoveryRecipe, *, domain: str) -> list[DiscoveryFinding]:
    items = page.locator(recipe.item_selector)
    count = min(items.count(), recipe.max_items)
    findings: list[DiscoveryFinding] = []
    for i in range(count):
        item = items.nth(i)
        title = ""
        if recipe.title_selector:
            try:
                title = (item.locator(recipe.title_selector).first.inner_text(timeout=3000) or "").strip()
            except Exception:
                title = ""
        if not title:
            try:
                title = (item.inner_text(timeout=3000) or "").strip().split("\n")[0][:500]
            except Exception:
                title = f"Website item {i + 1}"

        link = recipe.start_url
        if recipe.link_selector:
            try:
                href = item.locator(recipe.link_selector).first.get_attribute("href", timeout=2000)
                link = resolve_item_link(href, domain=domain, fallback=recipe.start_url)
            except Exception:
                pass

        description = ""
        if recipe.description_selector:
            try:
                description = (item.locator(recipe.description_selector).first.inner_text(timeout=2000) or "").strip()
            except Exception:
                description = ""

        findings.append(
            make_discovery_finding(title=title, source_url=link, description=description)
        )
    return findings


def run_playwright_discovery_sync(
    *,
    recipe: BrowserDiscoveryRecipe,
    domain: str,
    settings: AppSettings,
    cancel_check: Callable[[], bool],
) -> PlaywrightDiscoveryRunOutcome:
    from playwright.sync_api import sync_playwright

    from livelead.domain.browser.models import BrowserEngine
    from livelead.infrastructure.browser.chromium_path import require_chromium_executable

    if cancel_check():
        return PlaywrightDiscoveryRunOutcome(SourceRunStatus.SKIPPED, 0, 0, "cancelled", ())

    deadline = time.monotonic() + recipe.time_budget_ms / 1000.0
    exe = require_chromium_executable(settings, BrowserEngine.PLAYWRIGHT)
    pw = None
    browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=settings.browser_headless,
            executable_path=exe,
        )
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(min(settings.browser_navigation_timeout_ms, recipe.time_budget_ms))

        try:
            response = page.goto(recipe.start_url, wait_until="domcontentloaded")
        except Exception as exc:
            nav = classify_navigation_exception(exc, url=recipe.start_url)
            st = (
                SourceRunStatus.NEEDS_USER_ACTION
                if nav.outcome == NavigationOutcome.NEEDS_USER_ACTION
                else SourceRunStatus.FAILED
            )
            return PlaywrightDiscoveryRunOutcome(st, 0, 1, nav.error_summary, ())

        status_code = response.status if response else 0
        if status_code >= 400:
            nav = classify_http_status(status_code, url=recipe.start_url)
            st = (
                SourceRunStatus.NEEDS_USER_ACTION
                if nav.outcome == NavigationOutcome.NEEDS_USER_ACTION
                else SourceRunStatus.FAILED
            )
            return PlaywrightDiscoveryRunOutcome(st, 0, 1, nav.error_summary, ())

        if recipe.wait_for_selector:
            try:
                page.wait_for_selector(recipe.wait_for_selector, timeout=min(15_000, recipe.time_budget_ms))
            except Exception as exc:
                return PlaywrightDiscoveryRunOutcome(
                    SourceRunStatus.FAILED,
                    0,
                    1,
                    f"wait_for_selector_timeout:{exc}"[:500],
                    (),
                )

        if time.monotonic() > deadline or cancel_check():
            return PlaywrightDiscoveryRunOutcome(SourceRunStatus.FAILED, 0, 1, "time_budget_exceeded", ())

        if _detect_challenge(page, recipe):
            return PlaywrightDiscoveryRunOutcome(
                SourceRunStatus.NEEDS_USER_ACTION,
                0,
                1,
                "challenge_or_interstitial_detected",
                (),
            )

        findings = _extract_findings(page, recipe, domain=domain)
        pages = 1
        if not findings:
            return PlaywrightDiscoveryRunOutcome(
                SourceRunStatus.SUCCEEDED,
                0,
                pages,
                "no_items_extracted",
                (),
            )
        return PlaywrightDiscoveryRunOutcome(
            SourceRunStatus.SUCCEEDED,
            len(findings),
            pages,
            None,
            tuple(findings),
        )
    except Exception as exc:
        logger.warning("playwright_discovery_failed domain=%s err=%s", domain, exc)
        return PlaywrightDiscoveryRunOutcome(
            SourceRunStatus.FAILED,
            0,
            1,
            str(exc)[:500],
            (),
        )
    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass