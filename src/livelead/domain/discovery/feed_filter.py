"""Campaign keyword filtering for feed discoveries."""

from __future__ import annotations


def matches_discovery_keywords(
    text: str,
    *,
    positive: list[str],
    exclude: list[str],
) -> bool:
    hay = (text or "").lower()
    for ex in exclude:
        ex = (ex or "").strip().lower()
        if ex and ex in hay:
            return False
    positives = [p.strip().lower() for p in positive if p and p.strip()]
    if not positives:
        return True
    return any(p in hay for p in positives)
