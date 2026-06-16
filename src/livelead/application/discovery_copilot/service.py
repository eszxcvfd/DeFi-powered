"""Discovery copilot application service (US-037)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.query_expansion.service import QueryExpansionService
from livelead.domain.discovery_copilot.grounding import (
    grounding_keywords,
    question_within_discovery_scope,
)
from livelead.domain.discovery_copilot.schema import (
    response_to_dict,
    validate_structured_response,
)
from livelead.domain.query_expansion.models import (
    QueryExpansionVariant,
    QueryVariantSource,
    QueryVariantType,
)
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.ai.discovery_copilot_factory import (
    CopilotProviderNotConfiguredError,
    build_discovery_copilot_provider,
)
from livelead.infrastructure.ai.discovery_copilot_provider import CopilotCampaignContext
from livelead.runtime.settings import AppSettings, parse_settings
from livelead.infrastructure.db.models import (
    CampaignRow,
    DiscoveryCopilotResponseRow,
    QueryExpansionSetRow,
)
from livelead.infrastructure.db.repositories.discovery_copilot import DiscoveryCopilotRepository
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source


class DiscoveryCopilotValidationError(ValueError):
    pass


class DiscoveryCopilotService:
    def __init__(
        self, session: AsyncSession, settings: AppSettings | None = None
    ) -> None:
        self._session = session
        self._repo = DiscoveryCopilotRepository(session)
        self._settings = settings or parse_settings()
        try:
            self._provider = build_discovery_copilot_provider(self._settings)
        except CopilotProviderNotConfiguredError:
            self._provider = None

    async def _campaign(self, campaign_id: UUID, organization_id: UUID) -> CampaignRow:
        result = await self._session.execute(
            select(CampaignRow).where(
                CampaignRow.id == str(campaign_id),
                CampaignRow.organization_id == str(organization_id),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise DiscoveryCopilotValidationError("campaign not found")
        return row

    async def _runnable_sources(
        self, campaign_id: UUID, organization_id: UUID
    ) -> tuple[list[str], list[str]]:
        src_repo = SourceRepository(self._session)
        ids = await src_repo.list_campaign_source_ids(campaign_id, organization_id)
        runnable_ids: list[str] = []
        labels: list[str] = []
        for sid in ids:
            row = await src_repo.get(sid, organization_id)
            if not row:
                continue
            if evaluate_source_policy(row_to_source(row)).runnable:
                runnable_ids.append(str(sid))
                labels.append(row.name or row.domain)
        return runnable_ids, labels

    async def respond(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        question: str,
        actor: str,
    ) -> DiscoveryCopilotResponseRow:
        ok, reason = question_within_discovery_scope(question)
        if not ok:
            raise DiscoveryCopilotValidationError(reason or "invalid question")
        if self._provider is None:
            raise DiscoveryCopilotValidationError(
                "Discovery copilot requires Google AI Studio: set LIVELEAD_DISCOVERY_COPILOT_PROVIDER=gemini "
                "and LIVELEAD_GOOGLE_AI_STUDIO_API_KEY in the repo-root .env file"
            )

        camp = await self._campaign(campaign_id, organization_id)
        positive = [str(x) for x in json.loads(camp.positive_keywords_json or "[]") if x]
        runnable_ids, labels = await self._runnable_sources(campaign_id, organization_id)
        tokens = grounding_keywords(camp.name, camp.target_industry or "", positive)

        ctx = CopilotCampaignContext(
            campaign_id=str(campaign_id),
            campaign_name=camp.name,
            target_industry=camp.target_industry or "",
            positive_keywords=positive,
            runnable_source_ids=runnable_ids,
            runnable_source_labels=labels,
            context_tokens=tokens,
        )
        structured = self._provider.respond(question.strip(), ctx)
        validate_structured_response(response_to_dict(structured))
        payload = response_to_dict(structured)

        return await self._repo.create(
            organization_id=organization_id,
            campaign_id=campaign_id,
            question=question.strip(),
            response=payload,
            provider_id=structured.provider_id,
            model_id=structured.model_id,
            confidence=structured.confidence,
            created_by=actor,
        )

    async def list_recent(
        self, campaign_id: UUID, organization_id: UUID
    ) -> list[DiscoveryCopilotResponseRow]:
        return await self._repo.list_recent_for_campaign(campaign_id, organization_id)

    async def accept_into_query_expansion(
        self,
        *,
        response_id: UUID,
        organization_id: UUID,
        campaign_id: UUID,
        actor: str,
    ) -> tuple[DiscoveryCopilotResponseRow, QueryExpansionSetRow]:
        row = await self._repo.get(response_id, organization_id)
        if not row or row.campaign_id != str(campaign_id):
            raise DiscoveryCopilotValidationError("copilot response not found")
        if row.accepted_at:
            raise DiscoveryCopilotValidationError("copilot response already accepted")

        payload = json.loads(row.response_json or "{}")
        structured = validate_structured_response(payload)
        framing = structured.proposed_query_framing or [
            c.text for c in structured.claims[:1]
        ]

        variants: list[QueryExpansionVariant] = []
        for phrase in framing[:20]:
            variants.append(
                QueryExpansionVariant(
                    text=phrase,
                    variant_type=QueryVariantType.INDUSTRY_PHRASE,
                    source=QueryVariantSource.AI,
                    confidence=structured.confidence,
                    assumption="Suggested by discovery copilot; review before approval",
                )
            )

        qsvc = QueryExpansionService(self._session)
        expansion_row = await qsvc.create_from_copilot_variants(
            organization_id=organization_id,
            campaign_id=campaign_id,
            variants=variants,
            actor=actor,
            confidence=structured.confidence,
        )
        await self._repo.mark_accepted(
            row, accepted_by=actor, query_expansion_set_id=expansion_row.id
        )
        return row, expansion_row