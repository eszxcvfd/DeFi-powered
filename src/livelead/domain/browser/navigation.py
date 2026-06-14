"""Classify browser navigation outcomes for supervised sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NavigationOutcome(StrEnum):
    OK = "ok"
    NEEDS_USER_ACTION = "needs_user_action"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class NavigationResult:
    outcome: NavigationOutcome
    user_message: str
    error_summary: str | None = None


def classify_http_status(status: int, *, url: str) -> NavigationResult:
    short = url[:240]
    if status < 400:
        return NavigationResult(outcome=NavigationOutcome.OK, user_message="")
    if status in (401, 403, 407, 429):
        return NavigationResult(
            outcome=NavigationOutcome.NEEDS_USER_ACTION,
            user_message=(
                f"Site returned HTTP {status} (access blocked or login required). "
                "Many publishers block automated browsers — open the link in your normal browser, "
                "or set LIVELEAD_BROWSER_HEADLESS=false and retry to complete any challenge manually."
            ),
            error_summary=f"HTTP {status} blocked for {short}",
        )
    if status == 404:
        return NavigationResult(
            outcome=NavigationOutcome.FAILED,
            user_message="Page not found (HTTP 404). The discovery link may be stale or incorrect.",
            error_summary=f"HTTP 404 for {short}",
        )
    return NavigationResult(
        outcome=NavigationOutcome.FAILED,
        user_message=f"Server returned HTTP {status}.",
        error_summary=f"HTTP {status} for {short}",
    )


def classify_navigation_exception(exc: BaseException, *, url: str) -> NavigationResult:
    msg = str(exc).lower()
    short = url[:240]
    if "timeout" in msg or "timed out" in msg:
        return NavigationResult(
            outcome=NavigationOutcome.NEEDS_USER_ACTION,
            user_message="Navigation timed out. Check network or retry with a shorter path (e.g. site homepage).",
            error_summary=f"timeout for {short}",
        )
    if "net::err" in msg or "connection" in msg:
        return NavigationResult(
            outcome=NavigationOutcome.FAILED,
            user_message="Network error reaching the URL.",
            error_summary=str(exc)[:500],
        )
    return NavigationResult(
        outcome=NavigationOutcome.FAILED,
        user_message="Browser navigation failed.",
        error_summary=str(exc)[:500],
    )
