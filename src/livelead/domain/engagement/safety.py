"""Anti-spam and unsupported-action guardrails for engagement tasks."""

from __future__ import annotations

import re

from livelead.domain.engagement.models import EngagementPhase

FORBIDDEN_TASK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bmass\s+(dm|email|message)",
        r"\bbulk\s+(spam|message|email)",
        r"\bscrape\s+attendee",
        r"\bharvest\s+email",
        r"\bfake\s+review",
        r"\bclick\s*farm",
        r"\bauto\s*post\b",
        r"\bguaranteed\s+roi\b",
        r"\b100%\s+conversion\b",
        r"\bdeceptive\b",
        r"\bimpersonat",
    )
)


def task_text_is_unsafe(title: str, rationale: str) -> bool:
    combined = f"{title} {rationale}"
    return any(p.search(combined) for p in FORBIDDEN_TASK_PATTERNS)


def filter_safe_tasks(
    tasks: list[tuple[EngagementPhase, str, str]],
) -> list[tuple[EngagementPhase, str, str]]:
    safe: list[tuple[EngagementPhase, str, str]] = []
    for phase, title, rationale in tasks:
        if task_text_is_unsafe(title, rationale):
            continue
        safe.append((phase, title.strip(), rationale.strip()))
    return safe
