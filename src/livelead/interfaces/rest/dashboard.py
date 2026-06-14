"""Dashboard reporting REST (US-014)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.reporting.service import DashboardOverviewService
from livelead.domain.reporting.time_window import InvalidDashboardTimeWindow
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.dashboard_schemas import (
    DashboardMetricCardSchema,
    DashboardOverviewSchema,
    DashboardTimeWindowSchema,
    WidgetFreshnessSchema,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(tags=["reporting"])


def _to_schema(overview) -> DashboardOverviewSchema:
    return DashboardOverviewSchema(
        time_window=DashboardTimeWindowSchema(
            start=overview.time_window.start,
            end=overview.time_window.end,
            preset=overview.time_window.preset,
        ),
        widgets=[
            DashboardMetricCardSchema(
                key=w.key,
                label=w.label,
                availability=w.availability.value,
                value=w.value,
                freshness=WidgetFreshnessSchema(
                    last_updated_at=w.freshness.last_updated_at,
                    source=w.freshness.source,
                ),
                unavailable_reason=w.unavailable_reason,
            )
            for w in overview.widgets
        ],
        generated_at=overview.generated_at,
    )


@router.get("/reporting/dashboard-overview", response_model=DashboardOverviewSchema)
async def get_dashboard_overview(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    preset: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = DashboardOverviewService(session)
    try:
        overview = await svc.get_overview(
            tenant.organization_id,
            start=start,
            end=end,
            preset=preset,
        )
    except InvalidDashboardTimeWindow as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_schema(overview)
