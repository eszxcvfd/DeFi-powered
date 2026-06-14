"""Reporting endpoints — funnel (US-016), source/content performance (US-017/018)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.reporting.content_effectiveness_service import (
    ContentEffectivenessReportService,
)
from livelead.application.reporting.funnel_service import FunnelReportService
from livelead.application.reporting.source_performance_service import SourcePerformanceReportService
from livelead.domain.reporting.content_effectiveness import InvalidContentGrouping
from livelead.domain.reporting.source_performance import InvalidSourceGrouping
from livelead.domain.reporting.time_window import InvalidDashboardTimeWindow
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.content_effectiveness_schemas import (
    ContentEffectivenessFreshnessSchema,
    ContentEffectivenessMetricsSchema,
    ContentEffectivenessReportSchema,
    ContentEffectivenessRowSchema,
    ContentEffectivenessWindowSchema,
    UnattributedContentSummarySchema,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.funnel_schemas import (
    FunnelCohortSchema,
    FunnelFreshnessSchema,
    FunnelReportSchema,
    FunnelStepSchema,
    UnattributedLeadSummarySchema,
)
from livelead.interfaces.rest.source_performance_schemas import (
    SourcePerformanceFreshnessSchema,
    SourcePerformanceMetricsSchema,
    SourcePerformanceReportSchema,
    SourcePerformanceRowSchema,
    SourcePerformanceWindowSchema,
    UnattributedSourceSummarySchema,
)

router = APIRouter(tags=["reporting"])


def _to_schema(report) -> FunnelReportSchema:
    unattributed = None
    if report.unattributed:
        unattributed = UnattributedLeadSummarySchema(
            manual_leads_in_cohort=report.unattributed.manual_leads_in_cohort,
            explanation=report.unattributed.explanation,
        )
    return FunnelReportSchema(
        cohort=FunnelCohortSchema(
            start=report.cohort.start,
            end=report.cohort.end,
            preset=report.cohort.preset,
            rule=report.cohort.rule,
        ),
        steps=[
            FunnelStepSchema(key=s.key, label=s.label, count=s.count, note=s.note)
            for s in report.steps
        ],
        unattributed=unattributed,
        freshness=FunnelFreshnessSchema(
            last_updated_at=report.freshness.last_updated_at,
            source=report.freshness.source,
        ),
        generated_at=report.generated_at,
    )


@router.get("/reports/funnel", response_model=FunnelReportSchema)
async def get_funnel_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    preset: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = FunnelReportService(session)
    try:
        report = await svc.get_report(
            tenant.organization_id,
            start=start,
            end=end,
            preset=preset,
        )
    except InvalidDashboardTimeWindow as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_schema(report)


def _source_performance_to_schema(report) -> SourcePerformanceReportSchema:
    unattributed = None
    if report.unattributed:
        unattributed = UnattributedSourceSummarySchema(
            events_without_source_link=report.unattributed.events_without_source_link,
            leads_without_group_key=report.unattributed.leads_without_group_key,
            explanation=report.unattributed.explanation,
        )
    return SourcePerformanceReportSchema(
        grouping=report.grouping.value,
        grouping_label=report.grouping_label,
        window=SourcePerformanceWindowSchema(
            start=report.window.start,
            end=report.window.end,
            preset=report.window.preset,
        ),
        rows=[
            SourcePerformanceRowSchema(
                group_key=r.group_key,
                group_label=r.group_label,
                metrics=SourcePerformanceMetricsSchema(
                    events_discovered=r.metrics.events_discovered,
                    events_prioritized=r.metrics.events_prioritized,
                    leads_created=r.metrics.leads_created,
                    opportunities=r.metrics.opportunities,
                ),
            )
            for r in report.rows
        ],
        unattributed=unattributed,
        freshness=SourcePerformanceFreshnessSchema(
            last_updated_at=report.freshness.last_updated_at,
            source=report.freshness.source,
        ),
        generated_at=report.generated_at,
    )


@router.get("/reports/source-performance", response_model=SourcePerformanceReportSchema)
async def get_source_performance_report(
    grouping: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    preset: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = SourcePerformanceReportService(session)
    try:
        report = await svc.get_report(
            tenant.organization_id,
            grouping=grouping,
            start=start,
            end=end,
            preset=preset,
        )
    except InvalidDashboardTimeWindow as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidSourceGrouping as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _source_performance_to_schema(report)


def _content_effectiveness_to_schema(report) -> ContentEffectivenessReportSchema:
    unattributed = None
    if report.unattributed:
        unattributed = UnattributedContentSummarySchema(
            used_content_without_metadata=report.unattributed.used_content_without_metadata,
            outcomes_without_content_link=report.unattributed.outcomes_without_content_link,
            explanation=report.unattributed.explanation,
        )
    return ContentEffectivenessReportSchema(
        grouping=report.grouping.value,
        grouping_label=report.grouping_label,
        window=ContentEffectivenessWindowSchema(
            start=report.window.start,
            end=report.window.end,
            preset=report.window.preset,
        ),
        rows=[
            ContentEffectivenessRowSchema(
                group_key=r.group_key,
                group_label=r.group_label,
                metrics=ContentEffectivenessMetricsSchema(
                    content_used=r.metrics.content_used,
                    outcomes_linked=r.metrics.outcomes_linked,
                    outcomes_contact=r.metrics.outcomes_contact,
                    outcomes_response=r.metrics.outcomes_response,
                    outcomes_meeting=r.metrics.outcomes_meeting,
                    outcomes_opportunity=r.metrics.outcomes_opportunity,
                ),
            )
            for r in report.rows
        ],
        unattributed=unattributed,
        freshness=ContentEffectivenessFreshnessSchema(
            last_updated_at=report.freshness.last_updated_at,
            source=report.freshness.source,
        ),
        correlation_note=report.correlation_note,
        generated_at=report.generated_at,
    )


@router.get("/reports/content-effectiveness", response_model=ContentEffectivenessReportSchema)
async def get_content_effectiveness_report(
    grouping: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    preset: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentEffectivenessReportService(session)
    try:
        report = await svc.get_report(
            tenant.organization_id,
            grouping=grouping,
            start=start,
            end=end,
            preset=preset,
        )
    except InvalidDashboardTimeWindow as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidContentGrouping as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _content_effectiveness_to_schema(report)
