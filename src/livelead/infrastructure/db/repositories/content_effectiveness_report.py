"""Content-effectiveness read queries (US-018)."""

import json
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reporting.content_effectiveness import (
    ContentEffectivenessMetrics,
    ContentEffectivenessRow,
    ContentGrouping,
    UnattributedContentSummary,
    sort_content_rows,
)
from livelead.infrastructure.db.models import (
    EventRow,
    GeneratedContentDraftRow,
    LeadActivityRow,
    LeadRow,
)


def _group_key_from_draft(
    grouping: ContentGrouping, settings_raw: str, template_version: str
) -> str | None:
    if grouping == ContentGrouping.TEMPLATE:
        key = (template_version or "").strip()
        return key or None
    try:
        data = json.loads(settings_raw or "{}")
    except json.JSONDecodeError:
        return None
    if grouping == ContentGrouping.CONTENT_TYPE:
        key = (data.get("content_type") or "").strip()
        return key or None
    if grouping == ContentGrouping.TONE:
        key = (data.get("tone") or "").strip()
        return key or None
    return None


def _label_for_key(grouping: ContentGrouping, key: str) -> str:
    if grouping == ContentGrouping.CONTENT_TYPE:
        return key.replace("_", " ").title()
    if grouping == ContentGrouping.TEMPLATE:
        return key
    return key.title() if key.islower() else key


class ContentEffectivenessReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_report_rows(
        self,
        organization_id: UUID,
        grouping: ContentGrouping,
        start: datetime,
        end_exclusive: datetime,
    ) -> tuple[
        tuple[ContentEffectivenessRow, ...], UnattributedContentSummary | None, datetime | None
    ]:
        org = str(organization_id)
        used_ts = func.coalesce(
            GeneratedContentDraftRow.updated_at, GeneratedContentDraftRow.generated_at
        )

        draft_q = (
            select(
                GeneratedContentDraftRow.id,
                GeneratedContentDraftRow.settings_json,
                GeneratedContentDraftRow.prompt_template_version,
                used_ts,
            )
            .join(EventRow, EventRow.id == GeneratedContentDraftRow.event_id)
            .where(
                EventRow.organization_id == org,
                GeneratedContentDraftRow.usage_status == "used",
                used_ts >= start,
                used_ts < end_exclusive,
            )
        )
        drafts = (await self._session.execute(draft_q)).all()

        draft_ids: set[str] = set()
        draft_to_group: dict[str, str] = {}
        missing_meta = 0
        freshness: list[datetime] = []

        for did, settings_json, template_version, ts in drafts:
            draft_ids.add(str(did))
            if ts:
                freshness.append(ts)
            gkey = _group_key_from_draft(grouping, settings_json, template_version)
            if not gkey:
                missing_meta += 1
                continue
            draft_to_group[str(did)] = gkey

        occurred = func.coalesce(LeadActivityRow.occurred_at, LeadActivityRow.created_at)
        outcome_q = (
            select(
                LeadActivityRow.linked_content_draft_id,
                LeadActivityRow.outcome_type,
                occurred,
            )
            .select_from(LeadActivityRow)
            .join(LeadRow, LeadRow.id == LeadActivityRow.lead_id)
            .where(
                LeadRow.organization_id == org,
                LeadActivityRow.kind == "outcome_recorded",
                LeadActivityRow.linked_content_draft_id != "",
                occurred >= start,
                occurred < end_exclusive,
            )
        )
        outcomes = (await self._session.execute(outcome_q)).all()

        used_by_group: dict[str, set[str]] = defaultdict(set)
        for did, gkey in draft_to_group.items():
            used_by_group[gkey].add(did)

        outcome_by_group: dict[str, list[str]] = defaultdict(list)
        unattributed_outcomes = 0
        for link_id, otype, ts in outcomes:
            if ts:
                freshness.append(ts)
            lid = str(link_id)
            if lid not in draft_ids:
                unattributed_outcomes += 1
                continue
            gkey = draft_to_group.get(lid)
            if not gkey:
                unattributed_outcomes += 1
                continue
            outcome_by_group[gkey].append(otype or "")

        keys = set(used_by_group) | set(outcome_by_group)
        rows: list[ContentEffectivenessRow] = []
        for key in keys:
            otypes = outcome_by_group.get(key, [])
            rows.append(
                ContentEffectivenessRow(
                    group_key=key,
                    group_label=_label_for_key(grouping, key),
                    metrics=ContentEffectivenessMetrics(
                        content_used=len(used_by_group.get(key, set())),
                        outcomes_linked=len(otypes),
                        outcomes_contact=otypes.count("contact"),
                        outcomes_response=otypes.count("response"),
                        outcomes_meeting=otypes.count("meeting"),
                        outcomes_opportunity=otypes.count("opportunity"),
                    ),
                )
            )

        last = max(freshness) if freshness else None
        unattributed = None
        if missing_meta > 0 or unattributed_outcomes > 0:
            unattributed = UnattributedContentSummary(
                used_content_without_metadata=missing_meta,
                outcomes_without_content_link=unattributed_outcomes,
            )
        return sort_content_rows(rows), unattributed, last
