"""Default public feed endpoints keyed by source domain."""

from __future__ import annotations

import json

DEFAULT_FEED_BY_DOMAIN: dict[str, str] = {
    "techcrunch.com": "https://techcrunch.com/feed/",
    "coindesk.com": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "defillama.com": "https://defillama.com/blog/rss.xml",
    "ethereum.org": "https://ethereum.org/en/feed.xml",
    "producthunt.com": "https://www.producthunt.com/feed",
    "hnrss.org": "https://hnrss.org/frontpage",
}


def feed_url_for_domain(domain: str, rate_limit_json: str | None) -> str | None:
    if rate_limit_json:
        try:
            data = json.loads(rate_limit_json)
            if isinstance(data, dict):
                for key in ("feed_url", "rss_url", "atom_url", "ics_url", "url"):
                    url = data.get(key)
                    if url and str(url).startswith(("http://", "https://")):
                        return str(url).strip()
        except json.JSONDecodeError:
            pass
    d = (domain or "").lower().removeprefix("www.")
    return DEFAULT_FEED_BY_DOMAIN.get(d)
