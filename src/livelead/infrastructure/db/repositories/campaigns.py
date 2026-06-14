import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.campaigns.models import Campaign
from livelead.infrastructure.db.mappers import icp_to_json, row_to_campaign, weights_to_json
from livelead.infrastructure.db.models import CampaignRow


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_organization(self, organization_id: UUID) -> list[Campaign]:
        org = str(organization_id)
        result = await self._session.execute(
            select(CampaignRow)
            .where(CampaignRow.organization_id == org)
            .order_by(CampaignRow.updated_at.desc())
        )
        return [row_to_campaign(r) for r in result.scalars().all()]

    async def get(self, campaign_id: UUID, organization_id: UUID) -> Campaign | None:
        result = await self._session.execute(
            select(CampaignRow).where(
                CampaignRow.id == str(campaign_id),
                CampaignRow.organization_id == str(organization_id),
            )
        )
        row = result.scalar_one_or_none()
        return row_to_campaign(row) if row else None

    async def add(self, row: CampaignRow) -> Campaign:
        self._session.add(row)
        await self._session.flush()
        return row_to_campaign(row)

    @staticmethod
    def new_row_from_payload(
        organization_id: UUID,
        payload: dict,
        *,
        parent_campaign_id: UUID | None = None,
        created_by_actor: str = "analyst",
        creation_source: str = "user",
        automation_run_id: str | None = None,
    ) -> CampaignRow:
        now = datetime.now(UTC)
        icp = payload["icp"]
        weights = payload["scoring_weights"]
        date_range = payload.get("date_range") or {}
        return CampaignRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            name=payload["name"].strip(),
            description=payload.get("description", ""),
            target_industry=payload.get("target_industry", ""),
            product_or_service_focus=payload.get("product_or_service_focus", ""),
            market_regions_json=json.dumps(list(payload.get("market_regions", []))),
            languages_json=json.dumps(list(payload.get("languages", []))),
            timezone=payload.get("timezone", "UTC"),
            date_start=date_range.get("start"),
            date_end=date_range.get("end"),
            positive_keywords_json=json.dumps(list(payload.get("positive_keywords", []))),
            exclude_keywords_json=json.dumps(list(payload.get("exclude_keywords", []))),
            icp_json=icp_to_json(icp),
            scoring_weights_json=weights_to_json(weights),
            status=payload.get("status", "draft"),
            parent_campaign_id=str(parent_campaign_id) if parent_campaign_id else None,
            created_by_actor=created_by_actor,
            creation_source=creation_source,
            automation_run_id=automation_run_id,
            created_at=now,
            updated_at=now,
        )

    async def apply_patch(self, row: CampaignRow, patch: dict) -> Campaign:
        if "name" in patch and patch["name"] is not None:
            row.name = patch["name"].strip()
        for field in (
            "description",
            "target_industry",
            "product_or_service_focus",
            "timezone",
            "status",
        ):
            if field in patch and patch[field] is not None:
                setattr(row, field, patch[field])
        if "market_regions" in patch and patch["market_regions"] is not None:
            row.market_regions_json = json.dumps(list(patch["market_regions"]))
        if "languages" in patch and patch["languages"] is not None:
            row.languages_json = json.dumps(list(patch["languages"]))
        if "positive_keywords" in patch and patch["positive_keywords"] is not None:
            row.positive_keywords_json = json.dumps(list(patch["positive_keywords"]))
        if "exclude_keywords" in patch and patch["exclude_keywords"] is not None:
            row.exclude_keywords_json = json.dumps(list(patch["exclude_keywords"]))
        if "date_range" in patch and patch["date_range"] is not None:
            dr = patch["date_range"]
            row.date_start = dr.get("start")
            row.date_end = dr.get("end")
        if "icp" in patch and patch["icp"] is not None:
            row.icp_json = icp_to_json(patch["icp"])
        if "scoring_weights" in patch and patch["scoring_weights"] is not None:
            row.scoring_weights_json = weights_to_json(patch["scoring_weights"])
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row_to_campaign(row)
