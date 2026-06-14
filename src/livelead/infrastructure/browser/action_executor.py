"""Playwright read-only action execution (US-021)."""

from __future__ import annotations

import logging
from typing import Any

from livelead.domain.browser.action_policy import is_safe_navigate_url
from livelead.domain.browser.actions import BrowserActionLifecycle, BrowserActionType

logger = logging.getLogger("livelead.browser_actions")


def run_playwright_action(
    page: Any,
    *,
    action_type: BrowserActionType,
    params: dict[str, Any],
    timeout_ms: int,
    source_domain: str,
) -> dict[str, Any]:
    try:
        if action_type == BrowserActionType.NAVIGATE:
            url = str(params.get("url", ""))
            if not is_safe_navigate_url(url, source_domain=source_domain):
                return _out(
                    BrowserActionLifecycle.BLOCKED,
                    "Navigate blocked: URL host does not match source domain.",
                    policy_reason="navigate_host_mismatch",
                )
            resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            status = resp.status if resp else 0
            if status in (401, 403, 407, 429):
                return _out(
                    BrowserActionLifecycle.NEEDS_USER_ACTION,
                    f"Site returned HTTP {status}; complete access in your browser.",
                    current_url=page.url,
                )
            if status >= 400:
                return _out(
                    BrowserActionLifecycle.FAILED,
                    f"Navigation failed with HTTP {status}.",
                    current_url=page.url,
                )
            title = (page.title() or "")[:120]
            return _out(
                BrowserActionLifecycle.COMPLETED,
                f"Navigated to {page.url[:120]}",
                detail=title or None,
                current_url=page.url,
            )

        if action_type == BrowserActionType.SCROLL:
            delta = int(params.get("delta_y", 400))
            page.evaluate(f"window.scrollBy(0, {delta})")
            return _out(
                BrowserActionLifecycle.COMPLETED,
                f"Scrolled by {delta}px",
                current_url=page.url,
            )

        if action_type == BrowserActionType.OPEN_DETAIL:
            locator = _resolve_locator(page, params)
            if locator is None:
                return _out(
                    BrowserActionLifecycle.FAILED,
                    "No link found to open on this page.",
                    detail="Try Read page text, or open the article in your normal browser.",
                )
            try:
                locator.first.click(timeout=timeout_ms)
            except Exception as click_exc:
                return _classify_playwright_error(click_exc, action_type)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=min(timeout_ms, 15_000))
            except Exception:
                pass
            return _out(
                BrowserActionLifecycle.COMPLETED,
                f"Opened detail — now at {page.url[:120]}",
                current_url=page.url,
            )

        if action_type == BrowserActionType.READ_TEXT:
            sel = str(params.get("selector", "body"))[:500]
            max_chars = int(params.get("max_chars", 2000))
            try:
                text = page.locator(sel).first.inner_text(timeout=timeout_ms)
            except Exception as read_exc:
                if sel != "body":
                    try:
                        text = page.locator("body").first.inner_text(timeout=timeout_ms)
                    except Exception as body_exc:
                        return _classify_playwright_error(body_exc, action_type)
                else:
                    return _classify_playwright_error(read_exc, action_type)
            preview = " ".join((text or "").split())[:max_chars]
            if not preview.strip():
                return _out(
                    BrowserActionLifecycle.NEEDS_USER_ACTION,
                    "Page returned no readable text (paywall or block page).",
                    detail="Open the source URL in your browser to read the article.",
                    current_url=page.url,
                )
            return _out(
                BrowserActionLifecycle.COMPLETED,
                f"Read {len(preview)} characters from page",
                detail=preview[:500] if len(preview) > 500 else preview,
                text_preview=preview,
                current_url=page.url,
            )

        return _out(BrowserActionLifecycle.BLOCKED, "Unsupported action type.")
    except Exception as exc:
        return _classify_playwright_error(exc, action_type)


def _classify_playwright_error(
    exc: BaseException, action_type: BrowserActionType
) -> dict[str, Any]:
    msg = str(exc)
    lower = msg.lower()
    if "timeout" in lower or "timed out" in lower:
        return _out(
            BrowserActionLifecycle.TIMEOUT,
            f"{action_type.value} timed out.",
            detail=msg[:400],
        )
    if "not attached" in lower or "target closed" in lower or "has been closed" in lower:
        return _out(
            BrowserActionLifecycle.FAILED,
            "Browser tab closed or navigated away during the action.",
            detail=msg[:400],
            policy_reason="page_closed",
        )
    if "strict mode violation" in lower or ("waiting for" in lower and "locator" in lower):
        hint = (
            "No matching element on this page (common on blocked or empty error pages)."
            if action_type == BrowserActionType.OPEN_DETAIL
            else "Could not read text from the page."
        )
        return _out(BrowserActionLifecycle.FAILED, hint, detail=msg[:400])
    logger.warning("browser_action_failed type=%s err=%s", action_type, exc)
    return _out(
        BrowserActionLifecycle.FAILED,
        f"{action_type.value} could not complete on this page.",
        detail=msg[:400],
    )


def _resolve_locator(page: Any, params: dict[str, Any]) -> Any | None:
    mode = params.get("locator_mode")
    if mode == "css_fallback" and params.get("selector"):
        return page.locator(params["selector"])
    if params.get("name"):
        return page.get_by_role(params.get("role", "link"), name=params["name"])
    if mode == "semantic_first_link":
        links = page.get_by_role("link")
        if links.count() == 0:
            return None
        return links.first
    return None


def _out(
    lifecycle: BrowserActionLifecycle,
    summary: str,
    *,
    detail: str | None = None,
    policy_reason: str | None = None,
    current_url: str | None = None,
    text_preview: str | None = None,
) -> dict[str, Any]:
    return {
        "lifecycle": lifecycle.value,
        "summary": summary,
        "detail": detail,
        "policy_reason": policy_reason,
        "current_url": current_url,
        "text_preview": text_preview,
    }
