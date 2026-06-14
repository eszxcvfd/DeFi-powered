"""Auto-provision Playwright browser connector from event source evidence URLs."""

from __future__ import annotations

from urllib.parse import urlparse


def domain_from_url(url: str) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    try:
        host = urlparse(raw).hostname
    except ValueError:
        return None
    if not host:
        return None
    return host.lower().removeprefix("www.")


def playwright_connector_name(domain: str) -> str:
    return f"Playwright · {domain}"


def auto_provision_domain(event_source_url: str, observation_urls: list[str]) -> str | None:
    for candidate in [event_source_url, *observation_urls]:
        d = domain_from_url(candidate)
        if d:
            return d
    return None
