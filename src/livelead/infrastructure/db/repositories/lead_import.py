"""Repository for the lead CSV import/export tables (US-050).

The repository is the only place that touches
`LeadImportJobRow` and `LeadImportRowRow`. Higher layers
call the application service so the bounded slice
remains the single source of truth for the import and
export mutations.
"""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.leads.import_export import (
    LeadImportClassification,
    LeadImportJob,
    LeadImportRow,
    LeadImportStatus,
)
from livelead.infrastructure.db.lead_import_mappers import row_to_import_job, row_to_import_row
from livelead.infrastructure.db.models import LeadImportJobRow, LeadImportRowRow


def _dumps(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


def _dumps_list(values: tuple[str, ...] | list[str]) -> str:
    return json.dumps(list(values), default=str)


class LeadImportJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, row: LeadImportJobRow) -> LeadImportJob:
        self._session.add(row)
        await self._session.flush()
        return row_to_import_job(row)

    async def get(self, job_id: UUID, organization_id: UUID) -> LeadImportJob | None:
        result = await self._session.execute(
            select(LeadImportJobRow).where(
                LeadImportJobRow.id == str(job_id),
                LeadImportJobRow.organization_id == str(organization_id),
            )
        )
        row = result.scalars().first()
        return row_to_import_job(row) if row else None

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LeadImportJob]:
        result = await self._session.execute(
            select(LeadImportJobRow)
            .where(LeadImportJobRow.organization_id == str(organization_id))
            .order_by(LeadImportJobRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [row_to_import_job(r) for r in result.scalars().all()]

    async def count_for_org(self, organization_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(LeadImportJobRow.id)).where(
                LeadImportJobRow.organization_id == str(organization_id)
            )
        )
        return int(result.scalar() or 0)

    async def update_status(
        self,
        job_id: UUID,
        organization_id: UUID,
        *,
        status: LeadImportStatus,
        created_rows: int | None = None,
        skipped_rows: int | None = None,
        error_message: str | None = None,
    ) -> LeadImportJob | None:
        result = await self._session.execute(
            select(LeadImportJobRow).where(
                LeadImportJobRow.id == str(job_id),
                LeadImportJobRow.organization_id == str(organization_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return None
        row.status = status.value
        if created_rows is not None:
            row.created_rows = int(created_rows)
        if skipped_rows is not None:
            row.skipped_rows = int(skipped_rows)
        if error_message is not None:
            row.error_message = error_message
        if status == LeadImportStatus.APPLIED:
            from datetime import UTC, datetime

            row.applied_at = datetime.now(UTC)
        await self._session.flush()
        return row_to_import_job(row)


class LeadImportRowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, row: LeadImportRowRow) -> LeadImportRow:
        self._session.add(row)
        await self._session.flush()
        return row_to_import_row(row)

    async def list_for_job(
        self,
        job_id: UUID,
        organization_id: UUID,
        *,
        classification: LeadImportClassification | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeadImportRow]:
        q = select(LeadImportRowRow).where(
            LeadImportRowRow.import_job_id == str(job_id),
            LeadImportRowRow.organization_id == str(organization_id),
        )
        if classification is not None:
            q = q.where(LeadImportRowRow.classification == classification.value)
        q = q.order_by(LeadImportRowRow.row_number.asc()).limit(limit).offset(offset)
        result = await self._session.execute(q)
        return [row_to_import_row(r) for r in result.scalars().all()]

    async def count_for_job(
        self,
        job_id: UUID,
        organization_id: UUID,
        *,
        classification: LeadImportClassification | None = None,
    ) -> int:
        q = select(func.count(LeadImportRowRow.id)).where(
            LeadImportRowRow.import_job_id == str(job_id),
            LeadImportRowRow.organization_id == str(organization_id),
        )
        if classification is not None:
            q = q.where(LeadImportRowRow.classification == classification.value)
        result = await self._session.execute(q)
        return int(result.scalar() or 0)

    async def get(self, row_id: UUID, organization_id: UUID) -> LeadImportRow | None:
        result = await self._session.execute(
            select(LeadImportRowRow).where(
                LeadImportRowRow.id == str(row_id),
                LeadImportRowRow.organization_id == str(organization_id),
            )
        )
        row = result.scalars().first()
        return row_to_import_row(row) if row else None

    async def update_after_apply(
        self,
        row_id: UUID,
        organization_id: UUID,
        *,
        classification: LeadImportClassification,
        created_lead_id: UUID | None,
    ) -> LeadImportRow | None:
        result = await self._session.execute(
            select(LeadImportRowRow).where(
                LeadImportRowRow.id == str(row_id),
                LeadImportRowRow.organization_id == str(organization_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return None
        row.classification = classification.value
        row.created_lead_id = str(created_lead_id) if created_lead_id else None
        await self._session.flush()
        return row_to_import_row(row)


def new_import_job_row(**kwargs: object) -> LeadImportJobRow:
    from datetime import UTC, datetime

    defaults: dict = {
        "id": str(uuid4()),
        "status": LeadImportStatus.PREVIEWED.value,
        "total_rows": 0,
        "ready_rows": 0,
        "duplicate_rows": 0,
        "invalid_rows": 0,
        "created_rows": 0,
        "skipped_rows": 0,
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    if "mapping_json" in defaults and isinstance(defaults["mapping_json"], dict):
        defaults["mapping_json"] = _dumps(defaults["mapping_json"])
    return LeadImportJobRow(**defaults)  # type: ignore[arg-type]


def new_import_row_row(**kwargs: object) -> LeadImportRowRow:
    from datetime import UTC, datetime

    defaults: dict = {
        "id": str(uuid4()),
        "classification": LeadImportClassification.INVALID.value,
        "error_codes_json": "[]",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    if "normalized_payload_json" in defaults and isinstance(
        defaults["normalized_payload_json"], dict
    ):
        defaults["normalized_payload_json"] = _dumps(defaults["normalized_payload_json"])
    if "error_codes_json" in defaults and isinstance(defaults["error_codes_json"], (tuple, list)):
        defaults["error_codes_json"] = _dumps_list(defaults["error_codes_json"])
    return LeadImportRowRow(**defaults)  # type: ignore[arg-type]


__all__ = [
    "LeadImportJobRepository",
    "LeadImportRowRepository",
    "new_import_job_row",
    "new_import_row_row",
]
