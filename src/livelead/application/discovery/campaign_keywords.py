"""Load campaign positive/exclude keywords for discovery filtering."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from livelead.infrastructure.db.models import CampaignRow


def campaign_keywords(session: Session, campaign_id: str) -> tuple[list[str], list[str]]:
    row = session.execute(
        select(CampaignRow).where(CampaignRow.id == campaign_id)
    ).scalar_one_or_none()
    if not row:
        return [], []
    pos = json.loads(row.positive_keywords_json or "[]")
    ex = json.loads(row.exclude_keywords_json or "[]")
    return (
        [str(x) for x in pos if x],
        [str(x) for x in ex if x],
    )
