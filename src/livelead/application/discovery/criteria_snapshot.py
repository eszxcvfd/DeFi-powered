"""Shared criteria snapshot for manual and scheduled discovery jobs."""

from __future__ import annotations

import json
from uuid import UUID

from livelead.infrastructure.db.models import CampaignRow


def build_criteria_snapshot(
    camp_row: CampaignRow,
    *,
    campaign_id: UUID,
    source_ids: list[str],
    schedule_id: str | None = None,
    query_expansion: dict | None = None,
    positive_keywords: list[str] | None = None,
) -> dict:
    base_positive = json.loads(camp_row.positive_keywords_json or "[]")
    criteria: dict = {
        "campaign_id": str(campaign_id),
        "campaign_name": camp_row.name,
        "source_ids": source_ids,
        "positive_keywords": positive_keywords if positive_keywords is not None else base_positive,
        "exclude_keywords": json.loads(camp_row.exclude_keywords_json or "[]"),
    }
    if query_expansion:
        criteria["query_expansion"] = query_expansion
    if schedule_id:
        criteria["discovery_schedule_id"] = schedule_id
        criteria["trigger"] = "scheduled"
    else:
        criteria["trigger"] = "manual"
    return criteria