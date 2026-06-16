from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.sources.models import SourceGovernance, SourcePolicy
from livelead.infrastructure.db.models import CampaignSourceRow, SourceRow
from livelead.infrastructure.db.source_mappers import policy_to_json, row_to_source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_organization(self, organization_id: UUID) -> list[SourceGovernance]:
        result = await self._session.execute(
            select(SourceRow)
            .where(SourceRow.organization_id == str(organization_id))
            .order_by(SourceRow.domain)
        )
        return [row_to_source(r) for r in result.scalars().all()]

    async def get(self, source_id: UUID, organization_id: UUID) -> SourceRow | None:
        result = await self._session.execute(
            select(SourceRow).where(
                SourceRow.id == str(source_id),
                SourceRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def add(self, row: SourceRow) -> SourceGovernance:
        self._session.add(row)
        await self._session.flush()
        return row_to_source(row)

    @staticmethod
    def new_row(organization_id: UUID, payload: dict) -> SourceRow:
        policy: SourcePolicy = payload["policy"]
        now = datetime.now(UTC)
        return SourceRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            name=payload["name"].strip(),
            domain=payload["domain"].strip().lower(),
            connector_type=payload["connector_type"],
            automation_engine=payload.get("automation_engine", "none"),
            authentication_mode=payload.get("authentication_mode", "none"),
            enabled=payload.get("enabled", True),
            approved=payload.get("approved", False),
            approved_by=payload.get("approved_by"),
            approved_at=payload.get("approved_at"),
            policy_json=policy_to_json(policy),
            rate_limit_json="{}",
            secret_ciphertext=payload.get("secret_ciphertext"),
            created_at=now,
            updated_at=now,
        )

    async def apply_patch(self, row: SourceRow, patch: dict) -> SourceGovernance:
        for field in (
            "name",
            "domain",
            "connector_type",
            "automation_engine",
            "authentication_mode",
            "enabled",
            "approved",
            "approved_by",
        ):
            if field in patch and patch[field] is not None:
                setattr(row, field, patch[field])
        if "approved" in patch and patch["approved"]:
            row.approved_at = patch.get("approved_at") or datetime.now(UTC)
        if "policy" in patch and patch["policy"] is not None:
            row.policy_json = policy_to_json(patch["policy"])
        if "secret_ciphertext" in patch:
            row.secret_ciphertext = patch["secret_ciphertext"]
        if "rate_limit_json" in patch and patch["rate_limit_json"] is not None:
            row.rate_limit_json = patch["rate_limit_json"]
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row_to_source(row)

    async def set_campaign_sources(
        self, campaign_id: UUID, organization_id: UUID, source_ids: list[UUID]
    ) -> None:
        cid = str(campaign_id)
        org = str(organization_id)
        await self._session.execute(
            delete(CampaignSourceRow).where(
                CampaignSourceRow.campaign_id == cid,
                CampaignSourceRow.organization_id == org,
            )
        )
        for sid in source_ids:
            self._session.add(
                CampaignSourceRow(campaign_id=cid, source_id=str(sid), organization_id=org)
            )
        await self._session.flush()

    async def list_campaign_source_ids(
        self, campaign_id: UUID, organization_id: UUID
    ) -> list[UUID]:
        result = await self._session.execute(
            select(CampaignSourceRow.source_id).where(
                CampaignSourceRow.campaign_id == str(campaign_id),
                CampaignSourceRow.organization_id == str(organization_id),
            )
        )
        return [UUID(x) for x in result.scalars().all()]
