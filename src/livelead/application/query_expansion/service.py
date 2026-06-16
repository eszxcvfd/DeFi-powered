"""Query expansion application service (US-036)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.query_expansion.generator import generate_candidate_variants
from livelead.domain.query_expansion.models import (
    QueryExpansionGenerationMode,
    QueryExpansionSetStatus,
    QueryExpansionVariant,
    QueryVariantSource,
    QueryVariantType,
)
from livelead.domain.query_expansion.rules import (
    active_variants,
    derive_status_after_save,
    may_use_for_discovery_run,
    merge_expanded_keywords,
    set_requires_review,
    variant_to_dict,
)
from livelead.infrastructure.db.models import CampaignRow, QueryExpansionSetRow
from livelead.infrastructure.db.repositories.query_expansion import (
    QueryExpansionRepository,
    variants_from_json,
)


class QueryExpansionValidationError(ValueError):
    pass


class QueryExpansionBlockedError(ValueError):
    """Discovery cannot use unapproved AI expansion."""


def snapshot_from_row(
    row: QueryExpansionSetRow,
    *,
    base_positive: list[str],
) -> dict:
    variants = variants_from_json(row.variants_json)
    expanded = merge_expanded_keywords(base_positive, variants)
    return {
        "expansion_set_id": row.id,
        "expansion_set_version": row.version,
        "generation_mode": row.generation_mode,
        "status": row.status,
        "variants": [variant_to_dict(v) for v in variants if not v.removed],
        "expanded_positive_keywords": expanded,
        "query_mode": "approved_expansion" if active_variants(variants) else "raw_criteria",
    }


def parse_patch_variants(raw: list[dict]) -> list[QueryExpansionVariant]:
    out: list[QueryExpansionVariant] = []
    for item in raw:
        try:
            vtype = QueryVariantType(item.get("variant_type", QueryVariantType.USER.value))
        except ValueError:
            vtype = QueryVariantType.USER
        try:
            source = QueryVariantSource(item.get("source", QueryVariantSource.USER.value))
        except ValueError:
            source = QueryVariantSource.USER
        out.append(
            QueryExpansionVariant(
                text=str(item.get("text", "")),
                variant_type=vtype,
                source=source,
                confidence=item.get("confidence"),
                assumption=item.get("assumption"),
                user_edited=bool(item.get("user_edited", False)),
                removed=bool(item.get("removed", False)),
            )
        )
    return out


class QueryExpansionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = QueryExpansionRepository(session)

    async def _campaign_row(self, campaign_id: UUID, organization_id: UUID) -> CampaignRow:
        result = await self._session.execute(
            select(CampaignRow).where(
                CampaignRow.id == str(campaign_id),
                CampaignRow.organization_id == str(organization_id),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise QueryExpansionValidationError("campaign not found")
        return row

    def _base_keywords(self, camp: CampaignRow) -> list[str]:
        return [str(x) for x in json.loads(camp.positive_keywords_json or "[]") if x]

    async def generate(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        actor: str,
    ) -> QueryExpansionSetRow:
        camp = await self._campaign_row(campaign_id, organization_id)
        positive = self._base_keywords(camp)
        variants, mode = generate_candidate_variants(
            positive_keywords=positive,
            target_industry=camp.target_industry or "",
            description=camp.description or "",
        )
        status = (
            QueryExpansionSetStatus.PENDING_REVIEW
            if set_requires_review(variants, mode)
            else QueryExpansionSetStatus.DRAFT
        )
        return await self._repo.create_draft(
            organization_id=organization_id,
            campaign_id=campaign_id,
            generation_mode=mode,
            variants=variants,
            created_by=actor,
            status=status,
        )

    async def create_from_copilot_variants(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        variants: list[QueryExpansionVariant],
        actor: str,
        confidence: float,
    ) -> QueryExpansionSetRow:
        if not variants:
            raise QueryExpansionValidationError("no query framing to project")
        status = (
            QueryExpansionSetStatus.PENDING_REVIEW
            if set_requires_review(variants, QueryExpansionGenerationMode.AI_ASSISTED)
            else QueryExpansionSetStatus.DRAFT
        )
        return await self._repo.create_draft(
            organization_id=organization_id,
            campaign_id=campaign_id,
            generation_mode=QueryExpansionGenerationMode.AI_ASSISTED,
            variants=variants,
            created_by=actor,
            status=status,
        )

    async def get_latest(
        self, campaign_id: UUID, organization_id: UUID
    ) -> QueryExpansionSetRow | None:
        return await self._repo.latest_for_campaign(campaign_id, organization_id)

    async def patch_set(
        self,
        row: QueryExpansionSetRow,
        *,
        variants: list[QueryExpansionVariant],
        approve: bool,
        actor: str,
    ) -> QueryExpansionSetRow:
        mode = QueryExpansionGenerationMode(row.generation_mode)
        if approve and set_requires_review(variants, mode) and not active_variants(variants):
            # approving empty set is allowed (raw criteria only)
            pass
        status = derive_status_after_save(approve=approve, variants=variants, generation_mode=mode)
        if approve:
            await self._repo.supersede_approved_sets(
                UUID(row.campaign_id), UUID(row.organization_id)
            )
            row.version = (row.version or 1) + 1
            return await self._repo.update_variants(
                row, variants=variants, status=QueryExpansionSetStatus.APPROVED, approved_by=actor
            )
        return await self._repo.update_variants(row, variants=variants, status=status)

    async def resolve_for_discovery(
        self,
        *,
        campaign_id: UUID,
        organization_id: UUID,
        use_expansion: bool,
    ) -> tuple[dict | None, list[str], list[str]]:
        """Return (snapshot dict or None, positive keywords, exclude keywords)."""
        camp = await self._campaign_row(campaign_id, organization_id)
        base_pos = self._base_keywords(camp)
        exclude = [str(x) for x in json.loads(camp.exclude_keywords_json or "[]") if x]

        latest = await self._repo.latest_for_campaign(campaign_id, organization_id)
        if latest and not may_use_for_discovery_run(QueryExpansionSetStatus(latest.status)):
            if set_requires_review(
                variants_from_json(latest.variants_json),
                QueryExpansionGenerationMode(latest.generation_mode),
            ):
                if use_expansion:
                    raise QueryExpansionBlockedError(
                        "query expansion requires review before use with AI suggestions"
                    )

        approved = await self._repo.latest_approved_for_campaign(campaign_id, organization_id)
        if use_expansion and approved:
            snap = snapshot_from_row(approved, base_positive=base_pos)
            return snap, snap["expanded_positive_keywords"], exclude

        if use_expansion and not approved:
            return None, base_pos, exclude

        return None, base_pos, exclude