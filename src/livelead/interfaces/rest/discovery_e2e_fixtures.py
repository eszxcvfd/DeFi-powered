"""Test-only discovery fixtures (US-032 RSS, US-033 website HTML)."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

router = APIRouter(tags=["discovery-e2e-fixtures"])

_E2E_RSS = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>E2E Live Feed Summit</title><link>https://e2e-live-feed.local/e/1</link>
<description>webinar payments fintech</description></item>
</channel></rss>"""


@router.get("/dev/e2e-discovery-rss")
async def e2e_discovery_rss(request: Request) -> Response:
    settings = request.app.state.settings
    if not getattr(settings, "expose_e2e_discovery_rss_fixture", False):
        raise HTTPException(status_code=404, detail="not found")
    return Response(content=_E2E_RSS, media_type="application/rss+xml")


_E2E_WEBSITE_HTML = """<!DOCTYPE html>
<html><head><title>E2E Website Events</title></head>
<body>
<ul class="event-list">
  <li class="event-card">
    <a class="event-link" href="/e/1"><span class="event-title">E2E Website Playwright Summit</span></a>
    <p class="event-desc">webinar payments fintech public website</p>
  </li>
</ul>
</body></html>"""


@router.get("/dev/e2e-discovery-website")
async def e2e_discovery_website(request: Request) -> HTMLResponse:
    settings = request.app.state.settings
    if not getattr(settings, "expose_e2e_discovery_website_fixture", False):
        raise HTTPException(status_code=404, detail="not found")
    return HTMLResponse(content=_E2E_WEBSITE_HTML)