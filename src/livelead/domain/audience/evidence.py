"""Source-visible text and cue extraction for audience hypotheses (no campaign-only fiction)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from livelead.domain.events.models import CanonicalEvent, EventSourceObservation

_FORMAT_TERMS = re.compile(
    r"\b(webinar|summit|meetup|conference|workshop|roundtable|hackathon|demo\s*day)\b",
    re.IGNORECASE,
)
_PARTNER_TERMS = re.compile(
    r"\b(partner(?:ship)?s?|ecosystem|integrat(?:e|ion)|alliance|co-?sell|channel|reseller|sponsor)\b",
    re.IGNORECASE,
)
_B2B_TERMS = re.compile(r"\b(b2b|saas|enterprise|api|platform|developer|devops)\b", re.IGNORECASE)
_REFERRAL_TERMS = re.compile(
    r"\b(referral|introduc(?:e|tion)|network(?:ing)?|community|ambassador)\b",
    re.IGNORECASE,
)
# Fixture/mock discovery titles (see mock_findings_for_domain templates)
_MOCK_TITLE_MARKERS = (
    "b2b payments webinar",
    "fintech partnership summit",
    "cross-border compliance roundtable",
    "saas growth meetup",
    "developer api workshop",
)


def is_likely_fixture_event_title(title: str) -> bool:
    t = (title or "").lower()
    return any(m in t for m in _MOCK_TITLE_MARKERS)


def observable_event_text(event: CanonicalEvent, raw_titles: tuple[str, ...]) -> str:
    parts = [
        event.canonical_title,
        event.description,
        event.organizer,
        event.region or "",
        *raw_titles,
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def title_has_format_signal(text: str) -> bool:
    return bool(_FORMAT_TERMS.search(text))


def text_has_partner_signal(text: str) -> bool:
    return bool(_PARTNER_TERMS.search(text))


def text_has_b2b_signal(text: str) -> bool:
    return bool(_B2B_TERMS.search(text))


def text_has_referral_signal(text: str) -> bool:
    return bool(_REFERRAL_TERMS.search(text))


def icp_industry_in_event_text(icp_industry: str, event_text: str) -> bool:
    ind = (icp_industry or "").strip().lower()
    if len(ind) < 3:
        return False
    return ind in event_text.lower()


def region_observed_on_event(event: CanonicalEvent) -> str | None:
    """Region only when set on the canonical event (not campaign ICP fallback)."""
    r = (event.region or "").strip()
    return r if r else None


@dataclass(frozen=True, slots=True)
class ObservableSnapshot:
    text: str
    title: str
    has_description: bool
    has_organizer: bool
    observation_count: int


def snapshot_from_event(
    event: CanonicalEvent,
    observations: tuple[EventSourceObservation, ...],
) -> ObservableSnapshot:
    raw = tuple(o.raw_title for o in observations if o.raw_title)
    text = observable_event_text(event, raw)
    return ObservableSnapshot(
        text=text,
        title=(event.canonical_title or "").strip(),
        has_description=bool((event.description or "").strip()),
        has_organizer=bool((event.organizer or "").strip()),
        observation_count=len(observations),
    )


def confidence_from_observed_cues(*, observed_cues: int, text_len: int) -> float:
    score = 0.25 + min(0.35, observed_cues * 0.12)
    if text_len > 120:
        score += 0.1
    if text_len > 40:
        score += 0.05
    return round(min(0.92, max(0.22, score)), 2)
