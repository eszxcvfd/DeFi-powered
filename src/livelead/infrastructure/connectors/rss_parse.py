"""Parse RSS 2.0 and Atom feeds into discovery findings."""

from __future__ import annotations

import re
from html import unescape
from xml.etree import ElementTree as ET

from livelead.domain.discovery.finding import DiscoveryFinding

_STRIP_TAGS = re.compile(r"<[^>]+>")


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    raw = el.text or ""
    if not raw.strip() and len(el):
        raw = "".join(el.itertext())
    return unescape(_STRIP_TAGS.sub(" ", raw)).strip()


def _atom_link(entry: ET.Element) -> str:
    atom = "http://www.w3.org/2005/Atom"
    for link in entry.findall(f"{{{atom}}}link"):
        href = link.get("href")
        if href and link.get("rel", "alternate") in ("alternate", ""):
            return href
    id_el = entry.find(f"{{{atom}}}id")
    return _text(id_el)


def parse_feed_xml(data: bytes, *, source_domain: str) -> list[DiscoveryFinding]:
    root = ET.fromstring(data)
    findings: list[DiscoveryFinding] = []
    atom = "http://www.w3.org/2005/Atom"

    if root.tag.endswith("feed") or "feed" in root.tag.lower():
        for entry in root.findall(f"{{{atom}}}entry"):
            title = _text(entry.find(f"{{{atom}}}title"))
            link = _atom_link(entry) or f"https://{source_domain}/"
            summary = _text(entry.find(f"{{{atom}}}summary")) or _text(
                entry.find(f"{{{atom}}}content")
            )
            if title:
                findings.append(
                    DiscoveryFinding(
                        title=title[:500], source_url=link[:1024], description=summary[:2000]
                    )
                )
        return findings

    channel = root.find("channel")
    if channel is None:
        return findings
    for item in channel.findall("item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        desc = _text(item.find("description"))
        if not link:
            guid = _text(item.find("guid"))
            link = guid if guid.startswith("http") else f"https://{source_domain}/"
        if title:
            findings.append(
                DiscoveryFinding(title=title[:500], source_url=link[:1024], description=desc[:2000])
            )
    return findings
