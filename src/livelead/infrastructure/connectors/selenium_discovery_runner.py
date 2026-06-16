"""Sync Selenium WebDriver extraction for discovery jobs (infrastructure, US-034)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from livelead.domain.browser.models import BrowserEngine
from livelead.domain.browser.navigation import (
    NavigationOutcome,
    classify_navigation_exception,
)
from livelead.domain.discovery.browser_recipe import BrowserDiscoveryRecipe
from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.discovery.models import SourceRunStatus
from livelead.infrastructure.browser.chromium_path import require_chromium_executable
from livelead.infrastructure.connectors.browser_discovery_extraction import (
    body_indicates_challenge,
    make_discovery_finding,
    resolve_item_link,
)

if TYPE_CHECKING:
    from livelead.runtime.settings import AppSettings

logger = logging.getLogger("livelead.selenium_discovery")


@dataclass(frozen=True, slots=True)
class SeleniumDiscoveryRunOutcome:
    status: SourceRunStatus
    items_found: int
    pages_processed: int
    error_summary: str | None
    findings: tuple[DiscoveryFinding, ...]


def _challenge_selector_hits(driver: object, recipe: BrowserDiscoveryRecipe) -> tuple[str, ...]:
    from selenium.webdriver.common.by import By

    hits: list[str] = []
    for sel in recipe.challenge_selectors:
        try:
            if driver.find_elements(By.CSS_SELECTOR, sel):
                hits.append(sel)
        except Exception:
            continue
    return tuple(hits)


def _page_body_text(driver: object) -> str:
    from selenium.webdriver.common.by import By

    try:
        return (driver.find_element(By.TAG_NAME, "body").text or "")[:8000]
    except Exception:
        return ""


def _extract_findings(driver: object, recipe: BrowserDiscoveryRecipe, *, domain: str) -> list[DiscoveryFinding]:
    from selenium.webdriver.common.by import By

    items = driver.find_elements(By.CSS_SELECTOR, recipe.item_selector)
    count = min(len(items), recipe.max_items)
    findings: list[DiscoveryFinding] = []
    for i in range(count):
        item = items[i]
        title = ""
        if recipe.title_selector:
            try:
                title = (item.find_element(By.CSS_SELECTOR, recipe.title_selector).text or "").strip()
            except Exception:
                title = ""
        if not title:
            try:
                title = (item.text or "").strip().split("\n")[0][:500]
            except Exception:
                title = f"Website item {i + 1}"

        link = recipe.start_url
        if recipe.link_selector:
            try:
                href = item.find_element(By.CSS_SELECTOR, recipe.link_selector).get_attribute("href")
                link = resolve_item_link(href, domain=domain, fallback=recipe.start_url)
            except Exception:
                pass

        description = ""
        if recipe.description_selector:
            try:
                description = (
                    item.find_element(By.CSS_SELECTOR, recipe.description_selector).text or ""
                ).strip()
            except Exception:
                description = ""

        findings.append(
            make_discovery_finding(title=title, source_url=link, description=description)
        )
    return findings


def _build_chrome_driver(settings: AppSettings):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    exe = require_chromium_executable(settings, BrowserEngine.SELENIUM)
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = exe
    service = Service()
    return webdriver.Chrome(service=service, options=options)


def run_selenium_discovery_sync(
    *,
    recipe: BrowserDiscoveryRecipe,
    domain: str,
    settings: AppSettings,
    cancel_check: Callable[[], bool],
) -> SeleniumDiscoveryRunOutcome:
    try:
        import selenium  # noqa: F401
    except ImportError:
        return SeleniumDiscoveryRunOutcome(
            SourceRunStatus.FAILED,
            0,
            0,
            "selenium_package_not_installed",
            (),
        )

    if cancel_check():
        return SeleniumDiscoveryRunOutcome(SourceRunStatus.SKIPPED, 0, 0, "cancelled", ())

    deadline = time.monotonic() + recipe.time_budget_ms / 1000.0
    driver = None
    try:
        driver = _build_chrome_driver(settings)
        driver.set_page_load_timeout(
            min(settings.browser_navigation_timeout_ms, recipe.time_budget_ms) / 1000.0
        )
        try:
            driver.get(recipe.start_url)
        except Exception as exc:
            nav = classify_navigation_exception(exc, url=recipe.start_url)
            st = (
                SourceRunStatus.NEEDS_USER_ACTION
                if nav.outcome == NavigationOutcome.NEEDS_USER_ACTION
                else SourceRunStatus.FAILED
            )
            return SeleniumDiscoveryRunOutcome(st, 0, 1, nav.error_summary, ())

        # Selenium does not expose navigation response status uniformly; best-effort title check only.
        if recipe.wait_for_selector:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            try:
                WebDriverWait(driver, min(15, recipe.time_budget_ms // 1000)).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, recipe.wait_for_selector))
                )
            except Exception as exc:
                return SeleniumDiscoveryRunOutcome(
                    SourceRunStatus.FAILED,
                    0,
                    1,
                    f"wait_for_selector_timeout:{exc}"[:500],
                    (),
                )

        if time.monotonic() > deadline or cancel_check():
            return SeleniumDiscoveryRunOutcome(SourceRunStatus.FAILED, 0, 1, "time_budget_exceeded", ())

        body = _page_body_text(driver)
        if _challenge_selector_hits(driver, recipe) or body_indicates_challenge(body):
            return SeleniumDiscoveryRunOutcome(
                SourceRunStatus.NEEDS_USER_ACTION,
                0,
                1,
                "challenge_or_interstitial_detected",
                (),
            )

        findings = _extract_findings(driver, recipe, domain=domain)
        pages = 1
        if not findings:
            return SeleniumDiscoveryRunOutcome(
                SourceRunStatus.SUCCEEDED,
                0,
                pages,
                "no_items_extracted",
                (),
            )
        return SeleniumDiscoveryRunOutcome(
            SourceRunStatus.SUCCEEDED,
            len(findings),
            pages,
            None,
            tuple(findings),
        )
    except Exception as exc:
        logger.warning("selenium_discovery_failed domain=%s err=%s", domain, exc)
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            return SeleniumDiscoveryRunOutcome(
                SourceRunStatus.NEEDS_USER_ACTION,
                0,
                1,
                str(exc)[:500],
                (),
            )
        return SeleniumDiscoveryRunOutcome(
            SourceRunStatus.FAILED,
            0,
            1,
            str(exc)[:500],
            (),
        )
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass