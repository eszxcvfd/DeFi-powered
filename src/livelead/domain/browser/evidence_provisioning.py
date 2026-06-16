"""Auto-provision browser connectors from event source evidence URLs (US-033/US-034)."""

from __future__ import annotations

from urllib.parse import urlparse

# Engines provisioned from event evidence for supervised session + discovery paths.
EVIDENCE_BROWSER_ENGINES: tuple[str, ...] = ("playwright", "selenium")


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


def browser_connector_name(domain: str, automation_engine: str) -> str:
    engine = (automation_engine or "playwright").lower()
    if engine == "selenium":
        return f"Selenium · {domain}"
    if engine in ("cloakbrowser", "cloak"):
        return f"CloakBrowser · {domain}"
    return f"Playwright · {domain}"


def playwright_connector_name(domain: str) -> str:
    """Backward-compatible alias."""
    return browser_connector_name(domain, "playwright")


def auto_provision_domain(event_source_url: str, observation_urls: list[str]) -> str | None:
    for candidate in [event_source_url, *observation_urls]:
        d = domain_from_url(candidate)
        if d:
            return d
    return None