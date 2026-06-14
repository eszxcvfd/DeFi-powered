"""Normalized item from a real connector (feed, API, etc.)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscoveryFinding:
    title: str
    source_url: str
    description: str = ""
    organizer: str = ""
    region: str = ""
