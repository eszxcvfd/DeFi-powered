"""Sensitive-inference guardrails (FR-AUD-004)."""

from __future__ import annotations

import re

# Substrings that must not appear in audience outputs (protected-category speculation).
FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brace\b",
        r"\bethnic",
        r"\breligion\b",
        r"\bchristian\b",
        r"\bmuslim\b",
        r"\bhealth\s+status\b",
        r"\bdisability\b",
        r"\bsexual\s+orientation\b",
        r"\blgbtq",
        r"\bpolitical\b",
        r"\bvoter\b",
        r"\bpregnant\b",
    )
)


def contains_sensitive_inference(text: str) -> bool:
    return any(p.search(text) for p in FORBIDDEN_PATTERNS)


def sanitize_or_block(text: str) -> str | None:
    if contains_sensitive_inference(text):
        return None
    return text.strip()