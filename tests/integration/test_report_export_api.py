import pytest


@pytest.mark.asyncio
async def test_report_export_unsupported_type(client):
    r = await client.get(
        "/reports/export",
        params={"report_type": "roi", "format": "csv", "preset": "last_7_days"},
    )
    assert r.status_code == 400
    assert "unsupported" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_report_export_unsupported_format(client):
    r = await client.get(
        "/reports/export",
        params={"report_type": "funnel", "format": "xlsx", "preset": "last_7_days"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_report_export_funnel_csv(client):
    r = await client.get(
        "/reports/export",
        params={"report_type": "funnel", "format": "csv", "preset": "last_7_days"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert r.headers.get("X-Report-Type") == "funnel"
    assert r.headers.get("X-Export-Format") == "csv"
    assert b"step_key" in r.content


@pytest.mark.asyncio
async def test_report_export_dashboard_printable(client):
    r = await client.get(
        "/reports/export",
        params={"report_type": "dashboard", "format": "printable", "preset": "last_30_days"},
    )
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Dashboard overview" in r.content


@pytest.mark.asyncio
async def test_report_export_invalid_grouping(client):
    r = await client.get(
        "/reports/export",
        params={
            "report_type": "source_performance",
            "format": "csv",
            "preset": "last_7_days",
            "grouping": "invalid_dim",
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_report_export_invalid_date_range(client):
    r = await client.get(
        "/reports/export",
        params={
            "report_type": "content_effectiveness",
            "format": "csv",
            "start": "2026-06-10",
            "end": "2026-06-01",
            "grouping": "tone",
        },
    )
    assert r.status_code == 400
