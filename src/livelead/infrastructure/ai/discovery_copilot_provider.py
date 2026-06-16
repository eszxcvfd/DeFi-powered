"""Deterministic discovery copilot provider (US-037)."""

from __future__ import annotations

from dataclasses import dataclass

from livelead.domain.discovery_copilot.grounding import question_mentions_campaign_context
from livelead.domain.discovery_copilot.models import (
    CopilotClaim,
    CopilotEvidence,
    CopilotRiskCode,
    CopilotRiskFlag,
    DiscoveryCopilotStructuredResponse,
)


@dataclass
class CopilotCampaignContext:
    campaign_id: str
    campaign_name: str
    target_industry: str
    positive_keywords: list[str]
    runnable_source_ids: list[str]
    runnable_source_labels: list[str]
    context_tokens: set[str]


class DeterministicDiscoveryCopilotProvider:
    provider_id = "deterministic-discovery-copilot-v1"
    model_id = "grounded-template-v1"

    def respond(self, question: str, ctx: CopilotCampaignContext) -> DiscoveryCopilotStructuredResponse:
        grounded = question_mentions_campaign_context(question, ctx.context_tokens)
        keywords = ctx.positive_keywords[:8]
        framing = list(keywords)
        for kw in keywords[:3]:
            if ctx.target_industry:
                framing.append(f"{ctx.target_industry} {kw}".strip())
        if "livestream" in question.lower() or "stream" in question.lower():
            framing.append("livestream event discovery")
        framing = list(dict.fromkeys(f for f in framing if f))

        evidence: list[CopilotEvidence] = [
            CopilotEvidence(
                summary=f"Campaign '{ctx.campaign_name}' keywords: {', '.join(keywords) or 'none'}",
                source_ref="campaign.criteria",
            ),
        ]
        if ctx.runnable_source_labels:
            evidence.append(
                CopilotEvidence(
                    summary=f"Runnable sources: {', '.join(ctx.runnable_source_labels[:5])}",
                    source_ref="campaign.sources",
                )
            )

        assumptions = [
            "Recommendations are limited to configured campaign criteria and approved runnable sources.",
        ]
        if not ctx.runnable_source_ids:
            assumptions.append("No runnable sources are pinned; discovery may fall back to org defaults.")

        risk_flags: list[CopilotRiskFlag] = []
        if not grounded:
            risk_flags.append(
                CopilotRiskFlag(
                    code=CopilotRiskCode.UNGROUNDED_QUESTION.value,
                    message="Question may not reference current campaign context; review framing carefully.",
                )
            )
        if not keywords:
            risk_flags.append(
                CopilotRiskFlag(
                    code=CopilotRiskCode.WEAK_EVIDENCE.value,
                    message="Campaign has no positive keywords; query framing may be too broad.",
                )
            )
        if not ctx.runnable_source_ids:
            risk_flags.append(
                CopilotRiskFlag(
                    code=CopilotRiskCode.MISSING_SOURCE_COVERAGE.value,
                    message="No runnable campaign sources; source scope recommendation is empty.",
                )
            )

        confidence = 0.72
        if not grounded or not keywords:
            confidence = 0.45
        if risk_flags:
            confidence = min(confidence, 0.55)
            risk_flags.append(
                CopilotRiskFlag(
                    code=CopilotRiskCode.LOW_CONFIDENCE.value,
                    message="Copilot confidence is reduced due to weak grounding or missing coverage.",
                )
            )

        claim_text = (
            f"For '{ctx.campaign_name}', focus discovery on "
            f"{', '.join(framing[:4]) or 'campaign keywords'} using pinned runnable sources."
        )
        return DiscoveryCopilotStructuredResponse(
            claims=[CopilotClaim(text=claim_text, confidence=confidence)],
            evidence=evidence,
            confidence=confidence,
            assumptions=assumptions,
            risk_flags=risk_flags,
            proposed_query_framing=framing,
            recommended_source_ids=list(ctx.runnable_source_ids),
            provider_id=self.provider_id,
            model_id=self.model_id,
        )