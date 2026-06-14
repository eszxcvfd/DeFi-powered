"""Source-performance read queries (US-017)."""

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reporting.source_performance import (
    SourceGrouping,
    SourcePerformanceMetrics,
    SourcePerformanceRow,
    UnattributedSourceSummary,
    sort_rows,
)
from livelead.domain.scoring.models import PriorityLevel
from livelead.infrastructure.db.models import (
    CampaignRow,
    EventRow,
    EventScoreRow,
    EventSourceObservationRow,
    LeadActivityRow,
    LeadRow,
    SourceRow,
)

_PRIORITY = (
    PriorityLevel.VERY_HIGH.value,
    PriorityLevel.HIGH.value,
    PriorityLevel.WATCH.value,
)


class SourcePerformanceReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_report_rows(
        self,
        organization_id: UUID,
        grouping: SourceGrouping,
        start: datetime,
        end_exclusive: datetime,
    ) -> tuple[tuple[SourcePerformanceRow, ...], UnattributedSourceSummary | None, datetime | None]:
        org = str(organization_id)
        if grouping == SourceGrouping.CAMPAIGN:
            return await self._by_campaign(org, start, end_exclusive)
        if grouping == SourceGrouping.INDUSTRY:
            return await self._by_industry(org, start, end_exclusive)
        if grouping == SourceGrouping.PLATFORM:
            return await self._by_platform(org, start, end_exclusive)
        return await self._by_connector(org, start, end_exclusive)

    async def _campaign_labels(self, org: str) -> dict[str, tuple[str, str]]:
        q = select(CampaignRow.id, CampaignRow.name, CampaignRow.target_industry).where(
            CampaignRow.organization_id == org
        )
        out: dict[str, tuple[str, str]] = {}
        for cid, name, industry in (await self._session.execute(q)).all():
            out[str(cid)] = (name or cid, industry or "")
        return out

    async def _source_labels(self, org: str) -> dict[str, tuple[str, str]]:
        q = select(SourceRow.id, SourceRow.name, SourceRow.connector_type).where(
            SourceRow.organization_id == org
        )
        out: dict[str, tuple[str, str]] = {}
        for sid, name, ctype in (await self._session.execute(q)).all():
            out[str(sid)] = (name or sid, ctype or "unknown")
        return out

    async def _count_events_by_campaign(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> dict[str, tuple[int, datetime | None]]:
        q = (
            select(EventRow.campaign_id, func.count(), func.max(EventRow.observed_at))
            .where(
                EventRow.organization_id == org,
                EventRow.observed_at >= start,
                EventRow.observed_at < end_exclusive,
            )
            .group_by(EventRow.campaign_id)
        )
        return {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

    async def _count_prioritized_by_campaign(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> dict[str, tuple[int, datetime | None]]:
        q = (
            select(
                EventRow.campaign_id,
                func.count(func.distinct(EventRow.id)),
                func.max(EventScoreRow.calculated_at),
            )
            .select_from(EventScoreRow)
            .join(EventRow, EventRow.id == EventScoreRow.event_id)
            .where(
                EventRow.organization_id == org,
                EventScoreRow.superseded_at.is_(None),
                EventScoreRow.priority_level.in_(_PRIORITY),
                EventScoreRow.calculated_at >= start,
                EventScoreRow.calculated_at < end_exclusive,
            )
            .group_by(EventRow.campaign_id)
        )
        return {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

    async def _count_leads_by_campaign(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> dict[str, tuple[int, datetime | None]]:
        q = (
            select(LeadRow.campaign_id, func.count(), func.max(LeadRow.created_at))
            .where(
                LeadRow.organization_id == org,
                LeadRow.campaign_id.is_not(None),
                LeadRow.created_at >= start,
                LeadRow.created_at < end_exclusive,
            )
            .group_by(LeadRow.campaign_id)
        )
        return {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

    async def _count_leads_missing_campaign(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> int:
        q = select(func.count()).where(
            LeadRow.organization_id == org,
            LeadRow.campaign_id.is_(None),
            LeadRow.created_at >= start,
            LeadRow.created_at < end_exclusive,
        )
        return int((await self._session.execute(q)).scalar_one() or 0)

    async def _count_opportunities_by_campaign(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> dict[str, tuple[int, datetime | None]]:
        occurred = func.coalesce(LeadActivityRow.occurred_at, LeadActivityRow.created_at)
        q = (
            select(LeadRow.campaign_id, func.count(func.distinct(LeadRow.id)), func.max(occurred))
            .select_from(LeadActivityRow)
            .join(LeadRow, LeadRow.id == LeadActivityRow.lead_id)
            .where(
                LeadRow.organization_id == org,
                LeadRow.campaign_id.is_not(None),
                LeadActivityRow.kind == "outcome_recorded",
                LeadActivityRow.outcome_type == "opportunity",
                occurred >= start,
                occurred < end_exclusive,
            )
            .group_by(LeadRow.campaign_id)
        )
        return {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

    def _merge_campaign_keys(
        self,
        labels: dict[str, tuple[str, str]],
        *maps: dict[str, tuple[int, datetime | None]],
    ) -> tuple[list[SourcePerformanceRow], datetime | None]:
        keys: set[str] = set()
        for m in maps:
            keys.update(m.keys())
        freshness: list[datetime] = []
        rows: list[SourcePerformanceRow] = []
        for key in keys:
            ev = maps[0].get(key, (0, None))
            pr = maps[1].get(key, (0, None))
            ld = maps[2].get(key, (0, None))
            op = maps[3].get(key, (0, None))
            for ts in (ev[1], pr[1], ld[1], op[1]):
                if ts:
                    freshness.append(ts)
            name = labels.get(key, (key, ""))[0]
            rows.append(
                SourcePerformanceRow(
                    group_key=key,
                    group_label=name,
                    metrics=SourcePerformanceMetrics(
                        events_discovered=ev[0],
                        events_prioritized=pr[0],
                        leads_created=ld[0],
                        opportunities=op[0],
                    ),
                )
            )
        last = max(freshness) if freshness else None
        return rows, last

    async def _by_campaign(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> tuple[tuple[SourcePerformanceRow, ...], UnattributedSourceSummary | None, datetime | None]:
        labels = await self._campaign_labels(org)
        ev = await self._count_events_by_campaign(org, start, end_exclusive)
        pr = await self._count_prioritized_by_campaign(org, start, end_exclusive)
        ld = await self._count_leads_by_campaign(org, start, end_exclusive)
        op = await self._count_opportunities_by_campaign(org, start, end_exclusive)
        rows, last = self._merge_campaign_keys(labels, ev, pr, ld, op)
        missing_leads = await self._count_leads_missing_campaign(org, start, end_exclusive)
        unattributed = None
        if missing_leads > 0:
            unattributed = UnattributedSourceSummary(leads_without_group_key=missing_leads)
        return sort_rows(rows), unattributed, last

    async def _by_industry(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> tuple[tuple[SourcePerformanceRow, ...], UnattributedSourceSummary | None, datetime | None]:
        labels = await self._campaign_labels(org)
        ev_c = await self._count_events_by_campaign(org, start, end_exclusive)
        pr_c = await self._count_prioritized_by_campaign(org, start, end_exclusive)
        ld_c = await self._count_leads_by_campaign(org, start, end_exclusive)
        op_c = await self._count_opportunities_by_campaign(org, start, end_exclusive)

        def rollup(
            campaign_map: dict[str, tuple[int, datetime | None]],
        ) -> dict[str, tuple[int, datetime | None]]:
            agg: dict[str, list] = defaultdict(lambda: [0, None])
            for cid, (count, ts) in campaign_map.items():
                industry = (labels.get(cid, ("", ""))[1] or "").strip()
                if not industry:
                    continue
                agg[industry][0] += count
                if ts and (agg[industry][1] is None or ts > agg[industry][1]):
                    agg[industry][1] = ts
            return {k: (v[0], v[1]) for k, v in agg.items()}

        ev = rollup(ev_c)
        pr = rollup(pr_c)
        ld = rollup(ld_c)
        op = rollup(op_c)
        industry_labels = {k: (k, k) for k in set(ev) | set(pr) | set(ld) | set(op)}
        rows, last = self._merge_campaign_keys(industry_labels, ev, pr, ld, op)

        missing_industry_campaigns = 0
        for cid in set(ev_c) | set(pr_c) | set(ld_c) | set(op_c):
            if not (labels.get(cid, ("", ""))[1] or "").strip():
                missing_industry_campaigns += 1
        missing_leads = await self._count_leads_missing_campaign(org, start, end_exclusive)
        unattributed = None
        if missing_industry_campaigns > 0 or missing_leads > 0:
            unattributed = UnattributedSourceSummary(
                events_without_source_link=0,
                leads_without_group_key=missing_leads,
            )
        return sort_rows(rows), unattributed, last

    async def _events_by_source_dimension(
        self, org: str, start: datetime, end_exclusive: datetime, dim: str
    ) -> tuple[dict[str, tuple[int, datetime | None]], int]:
        """dim is connector_type or source_id column on SourceRow."""
        col = SourceRow.connector_type if dim == "platform" else SourceRow.id
        q = (
            select(col, func.count(func.distinct(EventRow.id)), func.max(EventRow.observed_at))
            .select_from(EventRow)
            .join(EventSourceObservationRow, EventSourceObservationRow.event_id == EventRow.id)
            .join(SourceRow, SourceRow.id == EventSourceObservationRow.source_id)
            .where(
                EventRow.organization_id == org,
                SourceRow.organization_id == org,
                EventRow.observed_at >= start,
                EventRow.observed_at < end_exclusive,
            )
            .group_by(col)
        )
        grouped = {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

        linked = (
            await self._session.execute(
                select(func.count(func.distinct(EventRow.id)))
                .select_from(EventRow)
                .join(EventSourceObservationRow, EventSourceObservationRow.event_id == EventRow.id)
                .where(
                    EventRow.organization_id == org,
                    EventRow.observed_at >= start,
                    EventRow.observed_at < end_exclusive,
                )
            )
        ).scalar_one() or 0
        total_ev = (
            await self._session.execute(
                select(func.count()).where(
                    EventRow.organization_id == org,
                    EventRow.observed_at >= start,
                    EventRow.observed_at < end_exclusive,
                )
            )
        ).scalar_one() or 0
        unattributed_events = int(total_ev) - int(linked)
        return grouped, max(0, unattributed_events)

    async def _prioritized_by_source_dimension(
        self, org: str, start: datetime, end_exclusive: datetime, dim: str
    ) -> dict[str, tuple[int, datetime | None]]:
        col = SourceRow.connector_type if dim == "platform" else SourceRow.id
        q = (
            select(
                col, func.count(func.distinct(EventRow.id)), func.max(EventScoreRow.calculated_at)
            )
            .select_from(EventScoreRow)
            .join(EventRow, EventRow.id == EventScoreRow.event_id)
            .join(EventSourceObservationRow, EventSourceObservationRow.event_id == EventRow.id)
            .join(SourceRow, SourceRow.id == EventSourceObservationRow.source_id)
            .where(
                EventRow.organization_id == org,
                SourceRow.organization_id == org,
                EventScoreRow.superseded_at.is_(None),
                EventScoreRow.priority_level.in_(_PRIORITY),
                EventScoreRow.calculated_at >= start,
                EventScoreRow.calculated_at < end_exclusive,
            )
            .group_by(col)
        )
        return {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

    async def _leads_by_source_dimension(
        self, org: str, start: datetime, end_exclusive: datetime, dim: str
    ) -> tuple[dict[str, tuple[int, datetime | None]], int]:
        col = SourceRow.connector_type if dim == "platform" else SourceRow.id
        q = (
            select(col, func.count(func.distinct(LeadRow.id)), func.max(LeadRow.created_at))
            .select_from(LeadRow)
            .join(EventRow, EventRow.id == LeadRow.event_id)
            .join(EventSourceObservationRow, EventSourceObservationRow.event_id == EventRow.id)
            .join(SourceRow, SourceRow.id == EventSourceObservationRow.source_id)
            .where(
                LeadRow.organization_id == org,
                SourceRow.organization_id == org,
                LeadRow.created_at >= start,
                LeadRow.created_at < end_exclusive,
            )
            .group_by(col)
        )
        grouped = {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

        total_ld = (
            await self._session.execute(
                select(func.count()).where(
                    LeadRow.organization_id == org,
                    LeadRow.created_at >= start,
                    LeadRow.created_at < end_exclusive,
                )
            )
        ).scalar_one() or 0
        linked_ld = (
            await self._session.execute(
                select(func.count(func.distinct(LeadRow.id)))
                .select_from(LeadRow)
                .join(EventRow, EventRow.id == LeadRow.event_id)
                .join(EventSourceObservationRow, EventSourceObservationRow.event_id == EventRow.id)
                .where(
                    LeadRow.organization_id == org,
                    LeadRow.created_at >= start,
                    LeadRow.created_at < end_exclusive,
                )
            )
        ).scalar_one() or 0
        return grouped, max(0, int(total_ld) - int(linked_ld))

    async def _opportunities_by_source_dimension(
        self, org: str, start: datetime, end_exclusive: datetime, dim: str
    ) -> dict[str, tuple[int, datetime | None]]:
        occurred = func.coalesce(LeadActivityRow.occurred_at, LeadActivityRow.created_at)
        col = SourceRow.connector_type if dim == "platform" else SourceRow.id
        q = (
            select(col, func.count(func.distinct(LeadRow.id)), func.max(occurred))
            .select_from(LeadActivityRow)
            .join(LeadRow, LeadRow.id == LeadActivityRow.lead_id)
            .join(EventRow, EventRow.id == LeadRow.event_id)
            .join(EventSourceObservationRow, EventSourceObservationRow.event_id == EventRow.id)
            .join(SourceRow, SourceRow.id == EventSourceObservationRow.source_id)
            .where(
                LeadRow.organization_id == org,
                SourceRow.organization_id == org,
                LeadActivityRow.kind == "outcome_recorded",
                LeadActivityRow.outcome_type == "opportunity",
                occurred >= start,
                occurred < end_exclusive,
            )
            .group_by(col)
        )
        return {str(k): (int(c or 0), ts) for k, c, ts in (await self._session.execute(q)).all()}

    async def _by_platform(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> tuple[tuple[SourcePerformanceRow, ...], UnattributedSourceSummary | None, datetime | None]:
        return await self._by_source_dim(org, start, end_exclusive, "platform")

    async def _by_connector(
        self, org: str, start: datetime, end_exclusive: datetime
    ) -> tuple[tuple[SourcePerformanceRow, ...], UnattributedSourceSummary | None, datetime | None]:
        return await self._by_source_dim(org, start, end_exclusive, "connector")

    async def _by_source_dim(
        self, org: str, start: datetime, end_exclusive: datetime, mode: str
    ) -> tuple[tuple[SourcePerformanceRow, ...], UnattributedSourceSummary | None, datetime | None]:
        dim = "platform" if mode == "platform" else "source_id"
        source_labels = await self._source_labels(org)
        ev, unattributed_events = await self._events_by_source_dimension(
            org, start, end_exclusive, dim
        )
        pr = await self._prioritized_by_source_dimension(org, start, end_exclusive, dim)
        ld, unattributed_leads = await self._leads_by_source_dimension(
            org, start, end_exclusive, dim
        )
        op = await self._opportunities_by_source_dimension(org, start, end_exclusive, dim)

        keys = set(ev) | set(pr) | set(ld) | set(op)
        freshness: list[datetime] = []
        rows: list[SourcePerformanceRow] = []
        for key in keys:
            ev_m = ev.get(key, (0, None))
            pr_m = pr.get(key, (0, None))
            ld_m = ld.get(key, (0, None))
            op_m = op.get(key, (0, None))
            for ts in (ev_m[1], pr_m[1], ld_m[1], op_m[1]):
                if ts:
                    freshness.append(ts)
            if mode == "platform":
                label = key
            else:
                label = source_labels.get(key, (key, ""))[0]
            rows.append(
                SourcePerformanceRow(
                    group_key=key,
                    group_label=label,
                    metrics=SourcePerformanceMetrics(
                        events_discovered=ev_m[0],
                        events_prioritized=pr_m[0],
                        leads_created=ld_m[0],
                        opportunities=op_m[0],
                    ),
                )
            )
        last = max(freshness) if freshness else None
        unattributed = None
        if unattributed_events > 0 or unattributed_leads > 0:
            unattributed = UnattributedSourceSummary(
                events_without_source_link=unattributed_events,
                leads_without_group_key=unattributed_leads,
            )
        return sort_rows(rows), unattributed, last
