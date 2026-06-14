"""Report export download endpoint (US-019)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.reporting.export_service import ReportExportService
from livelead.domain.reporting.content_effectiveness import InvalidContentGrouping
from livelead.domain.reporting.report_export import UnsupportedReportExport
from livelead.domain.reporting.source_performance import InvalidSourceGrouping
from livelead.domain.reporting.time_window import InvalidDashboardTimeWindow
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(tags=["reporting"])


@router.get("/reports/export")
async def export_report(
    report_type: str = Query(
        ..., description="dashboard | funnel | source_performance | content_effectiveness"
    ),
    format: str = Query(..., alias="format", description="csv | printable (pdf/html alias)"),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    preset: str | None = Query(default=None),
    grouping: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ReportExportService(session)
    try:
        artifact = await svc.export_report(
            tenant.organization_id,
            report_type_raw=report_type,
            format_raw=format,
            start=start,
            end=end,
            preset=preset,
            grouping=grouping,
        )
    except UnsupportedReportExport as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidDashboardTimeWindow as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidSourceGrouping as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidContentGrouping as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=artifact.body,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-Report-Type": artifact.report_type.value,
            "X-Export-Format": artifact.export_format.value,
            "X-Generated-At": artifact.generated_at.isoformat(),
        },
    )
