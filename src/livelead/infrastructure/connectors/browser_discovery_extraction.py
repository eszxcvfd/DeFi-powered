"""Shared challenge detection and finding shaping for browser discovery (US-033/US-034)."""

from __future__ import annotations

from livelead.domain.discovery.finding import DiscoveryFinding

_CHALLENGE_BODY_MARKERS = (
    "captcha",
    "verify you are human",
    "access denied",
    "bot detection",
)


def body_indicates_challenge(body_text: str) -> bool:
    lowered = (body_text or "").lower()
    return any(marker in lowered for marker in _CHALLENGE_BODY_MARKERS)


def resolve_item_link(href: str | None, *, domain: str, fallback: str) -> str:
    if not href:
        return fallback
    if href.startswith("http"):
        return href[:1024]
    if href.startswith("/"):
        return f"https://{domain}{href}"[:1024]
    return f"https://{domain}/{href}"[:1024]


def make_discovery_finding(
    *,
    title: str,
    source_url: str,
    description: str = "",
    organizer: str = "",
    region: str = "",
) -> DiscoveryFinding:
    return DiscoveryFinding(
        title=title[:500],
        source_url=source_url[:1024],
        description=description[:2000],
        organizer=organizer,
        region=region,
    )