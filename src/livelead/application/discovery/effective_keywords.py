"""Resolve discovery keywords from job criteria snapshot (US-036)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from livelead.application.discovery.campaign_keywords import campaign_keywords


def keywords_from_criteria_snapshot(
    session: Session,
    campaign_id: str,
    criteria_snapshot_json: str,
) -> tuple[list[str], list[str]]:
    snapshot = json.loads(criteria_snapshot_json or "{}")
    expansion = snapshot.get("query_expansion")
    if isinstance(expansion, dict):
        expanded = expansion.get("expanded_positive_keywords")
        if isinstance(expanded, list) and expanded:
            exclude = snapshot.get("exclude_keywords")
            if isinstance(exclude, list):
                ex = [str(x) for x in exclude if x]
            else:
                _, ex = campaign_keywords(session, campaign_id)
            return [str(x) for x in expanded if x], ex
    return campaign_keywords(session, campaign_id)