"""Grounding guards for discovery copilot questions (US-037)."""

from __future__ import annotations

import re

from livelead.domain.audience.safety import contains_sensitive_inference

_OFF_TOPIC_PATTERNS = (
    re.compile(r"\b(write|draft|email|linkedin|outreach)\b", re.I),
    re.compile(r"\b(recipe|cook|weather|stock price)\b", re.I),
)


def question_within_discovery_scope(question: str) -> tuple[bool, str | None]:
    q = (question or "").strip()
    if len(q) < 8:
        return False, "question too short for discovery planning"
    if len(q) > 2000:
        return False, "question exceeds maximum length"
    if contains_sensitive_inference(q):
        return False, "question references sensitive inference"
    for pat in _OFF_TOPIC_PATTERNS:
        if pat.search(q):
            return False, "question outside discovery planning scope"
    return True, None


def grounding_keywords(campaign_name: str, industry: str, keywords: list[str]) -> set[str]:
    tokens: set[str] = set()
    for blob in (campaign_name, industry, " ".join(keywords)):
        for part in re.split(r"[^\w]+", blob.lower()):
            if len(part) >= 3:
                tokens.add(part)
    return tokens


def question_mentions_campaign_context(question: str, context_tokens: set[str]) -> bool:
    if not context_tokens:
        return True
    q_tokens = {p for p in re.split(r"[^\w]+", question.lower()) if len(p) >= 3}
    return bool(q_tokens & context_tokens) or "livestream" in question.lower() or "discover" in question.lower()