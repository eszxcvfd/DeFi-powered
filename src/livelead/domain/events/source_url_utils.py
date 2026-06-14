"""Validate and pick HTTP URLs for browser launch and display."""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Legacy mock discovery URLs: https://{domain}/events/{domain-with-dashes}-{n}
_SYNTHETIC_EVENT_PATH = re.compile(
    r"^/events/[a-z0-9][a-z0-9-]*-\d+/?$",
    re.IGNORECASE,
)


def is_http_url(url: str) -> bool:
    u = (url or "").strip()
    return u.startswith("http://") or u.startswith("https://")


def is_synthetic_discovery_event_url(url: str) -> bool:
    """True for fixture URLs invented during mock discovery (not real feed links)."""
    raw = (url or "").strip()
    if not is_http_url(raw):
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    path = parsed.path or ""
    if not _SYNTHETIC_EVENT_PATH.match(path):
        return False
    host = (parsed.hostname or "").lower().removeprefix("www.")
    slug = path.rstrip("/").rsplit("/", 1)[-1]
    if not slug:
        return False
    # slug is like hnrss-org-1 -> prefix hnrss-org should relate to host hnrss.org
    slug_prefix = re.sub(r"-\d+$", "", slug).lower()
    host_key = host.replace(".", "-")
    return slug_prefix == host_key or slug_prefix.startswith(host_key.split("-")[0] + "-")


_UNRESOLVABLE_BROWSER_DOMAINS = frozenset({"example.com", "example.org", "example.net"})


def _domain_unresolvable_for_browser(domain: str) -> bool:
    d = (domain or "").strip().lower().removeprefix("www.")
    if not d:
        return True
    if d in _UNRESOLVABLE_BROWSER_DOMAINS:
        return True
    return d.endswith(".example.com") or d.endswith(".example.org") or d.endswith(".example.net")


def homepage_for_domain(domain: str) -> str:
    d = (domain or "").strip().lower().removeprefix("www.")
    if not d or _domain_unresolvable_for_browser(d):
        return "https://example.com/"
    return f"https://{d}/"


def pick_browser_launch_url(
    *,
    event_source_url: str,
    observation_urls: list[str],
    source_domain: str | None = None,
) -> str:
    """
    Choose a URL that is safe to open in a supervised browser session.
    Skips synthetic discovery fixture paths and falls back to a real homepage.
    """
    candidates: list[str] = []
    for u in [event_source_url, *observation_urls]:
        u = (u or "").strip()
        if u and is_http_url(u) and not is_synthetic_discovery_event_url(u):
            candidates.append(u)

    if candidates:
        return candidates[0]

    if source_domain:
        return homepage_for_domain(source_domain)

    for u in [event_source_url, *observation_urls]:
        u = (u or "").strip()
        if is_http_url(u):
            try:
                host = urlparse(u).hostname
            except ValueError:
                host = None
            if host and not _domain_unresolvable_for_browser(host):
                return homepage_for_domain(host)

    return "https://example.com/"
