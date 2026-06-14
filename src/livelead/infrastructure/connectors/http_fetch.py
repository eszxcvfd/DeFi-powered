"""HTTP fetch for feed connectors (stdlib)."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

USER_AGENT = "LiveLead-Discovery/1.0 (+event research)"


@dataclass(frozen=True, slots=True)
class FetchResult:
    status: int
    body: bytes
    content_type: str
    error: str | None


def fetch_url(url: str, *, timeout_sec: float = 25.0) -> FetchResult:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, text/calendar, application/xml, */*",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec, context=ctx) as resp:
            code = int(getattr(resp, "status", 200) or 200)
            body = resp.read(2_000_000)
            ct = resp.headers.get("Content-Type", "")
            return FetchResult(status=code, body=body, content_type=ct, error=None)
    except urllib.error.HTTPError as e:
        return FetchResult(status=e.code, body=b"", content_type="", error=str(e))
    except Exception as e:
        return FetchResult(status=0, body=b"", content_type="", error=str(e))
