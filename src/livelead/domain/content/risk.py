"""Risk flag rules for generated drafts."""

from __future__ import annotations

import re

from livelead.domain.audience.safety import contains_sensitive_inference
from livelead.domain.content.models import ContentRiskFlag, RiskFlagCode

_PROMO = re.compile(r"\b(guaranteed|100%|best ever|act now|limited time only)\b", re.I)
_UNSUPPORTED = re.compile(r"\b(we guarantee|certified roi|official partner of)\b", re.I)
_SPAM = re.compile(r"\b(buy now|click here!!!|free money)\b", re.I)


def evaluate_draft_risks(
    body: str,
    *,
    event_title: str,
    cta: str,
    prior_bodies: tuple[str, ...] = (),
) -> tuple[ContentRiskFlag, ...]:
    flags: list[ContentRiskFlag] = []
    if _PROMO.search(body) or _SPAM.search(body):
        flags.append(
            ContentRiskFlag(
                code=RiskFlagCode.OVERLY_PROMOTIONAL,
                message="Draft uses high-pressure or spam-like promotional language.",
            )
        )
    if _UNSUPPORTED.search(body):
        flags.append(
            ContentRiskFlag(
                code=RiskFlagCode.UNSUPPORTED_CLAIM,
                message="Draft may include unsupported or unverifiable claims.",
            )
        )
    if contains_sensitive_inference(body):
        flags.append(
            ContentRiskFlag(
                code=RiskFlagCode.SENSITIVE_TARGETING,
                message="Draft may reference protected or sensitive attributes.",
                severity="error",
            )
        )
    title_token = event_title.split()[0].lower() if event_title else ""
    if title_token and title_token not in body.lower() and len(event_title) > 8:
        flags.append(
            ContentRiskFlag(
                code=RiskFlagCode.LACKS_EVENT_RELEVANCE,
                message="Draft does not clearly reference the event context.",
            )
        )
    if len(cta) > 80 or "!!!" in cta:
        flags.append(
            ContentRiskFlag(
                code=RiskFlagCode.UNSUITABLE_CTA,
                message="CTA may be too aggressive or unsuitable for this channel.",
            )
        )
    for prior in prior_bodies:
        if prior.strip() and prior.strip() == body.strip():
            flags.append(
                ContentRiskFlag(
                    code=RiskFlagCode.REPETITIVE,
                    message="Draft duplicates another variant.",
                )
            )
            break
    return tuple(flags)
