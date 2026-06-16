"""Sync criteria attachment for worker/scheduler (US-036)."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from livelead.application.discovery.criteria_snapshot import build_criteria_snapshot
from livelead.application.query_expansion.service import (
    QueryExpansionBlockedError,
    snapshot_from_row,
)
from livelead.domain.query_expansion.models import (
    QueryExpansionGenerationMode,
    QueryExpansionSetStatus,
)
from livelead.domain.query_expansion.rules import may_use_for_discovery_run, set_requires_review
from livelead.infrastructure.db.models import CampaignRow, QueryExpansionSetRow
from livelead.infrastructure.db.repositories.query_expansion import variants_from_json


def _latest_pending_ai_block(session: Session, campaign_id: str, org_id: str) -> bool:
    row = session.execute(
        select(QueryExpansionSetRow)
        .where(
            QueryExpansionSetRow.campaign_id == campaign_id,
            QueryExpansionSetRow.organization_id == org_id,
        )
        .order_by(QueryExpansionSetRow.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not row:
        return False
    if may_use_for_discovery_run(QueryExpansionSetStatus(row.status)):
        return False
    return set_requires_review(
        variants_from_json(row.variants_json),
        QueryExpansionGenerationMode(row.generation_mode),
    )


def _latest_approved(session: Session, campaign_id: str, org_id: str) -> QueryExpansionSetRow | None:
    return session.execute(
        select(QueryExpansionSetRow)
        .where(
            QueryExpansionSetRow.campaign_id == campaign_id,
            QueryExpansionSetRow.organization_id == org_id,
            QueryExpansionSetRow.status == QueryExpansionSetStatus.APPROVED.value,
        )
        .order_by(QueryExpansionSetRow.approved_at.desc().nullslast(), QueryExpansionSetRow.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def build_discovery_criteria(
    session: Session,
    camp_row: CampaignRow,
    *,
    campaign_id: UUID,
    source_ids: list[str],
    organization_id: UUID,
    schedule_id: str | None = None,
    use_expansion: bool = True,
) -> dict:
    base_positive = [str(x) for x in json.loads(camp_row.positive_keywords_json or "[]") if x]
    org = str(organization_id)
    cid = str(campaign_id)

    if use_expansion and _latest_pending_ai_block(session, cid, org):
        raise QueryExpansionBlockedError(
            "query expansion requires review before use with AI suggestions"
        )

    expansion_snap: dict | None = None
    positive = base_positive
    if use_expansion:
        approved = _latest_approved(session, cid, org)
        if approved:
            expansion_snap = snapshot_from_row(approved, base_positive=base_positive)
            positive = expansion_snap["expanded_positive_keywords"]

    return build_criteria_snapshot(
        camp_row,
        campaign_id=campaign_id,
        source_ids=source_ids,
        schedule_id=schedule_id,
        query_expansion=expansion_snap,
        positive_keywords=positive,
    )