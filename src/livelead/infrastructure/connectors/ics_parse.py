"""Parse iCalendar (ICS) VEVENT entries."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from livelead.domain.discovery.finding import DiscoveryFinding

_VEVENT = re.compile(r"BEGIN:VEVENT(.*?)END:VEVENT", re.DOTALL | re.IGNORECASE)
_FIELD = re.compile(r"^([A-Z0-9-]+)(?:;[^:]*)?:(.*)$", re.MULTILINE)


def _unfold(ics: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", ics)


def parse_ics_text(text: str, *, source_domain: str) -> list[DiscoveryFinding]:
    body = _unfold(text)
    findings: list[DiscoveryFinding] = []
    for block in _VEVENT.findall(body):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            m = _FIELD.match(line.strip())
            if m:
                fields[m.group(1).upper()] = m.group(2).strip()
        title = fields.get("SUMMARY", "")
        url = fields.get("URL", "") or fields.get("UID", "")
        if url and not url.startswith("http"):
            url = f"https://{source_domain}/events/{urlparse(url).path or url}"
        desc = fields.get("DESCRIPTION", "")
        loc = fields.get("LOCATION", "")
        if title:
            findings.append(
                DiscoveryFinding(
                    title=title[:500],
                    source_url=(url or f"https://{source_domain}/")[:1024],
                    description=desc[:2000],
                    region=loc[:120],
                )
            )
        if len(findings) >= 80:
            break
    return findings
