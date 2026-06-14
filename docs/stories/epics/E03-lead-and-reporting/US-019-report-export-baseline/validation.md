# Validation

## Proof Strategy

This story is done only when LiveLead can export at least the current dashboard
and grouped reporting views using the user's selected filters, preserve
freshness or generated-at context, and produce both structured CSV and
human-readable printable output without depending on scheduled delivery or
external-sync stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Supported format mapping, report-type validation, CSV row shaping, printable metadata carry-through, and unsupported-combination errors. |
| Integration | Report-export endpoint behavior across dashboard, funnel, source-performance, and content-effectiveness requests; invalid-filter handling; and artifact metadata validation. |
| E2E | User exports a current report view, keeps the selected time range or grouping context, and receives clear feedback for success or unsupported combinations. |
| Platform | Story verify command keeps backend report-export flows and frontend reporting export affordances wired into the Harness matrix. |
| Performance | Export generation remains responsive for realistic report windows and grouped row counts without blocking the UI unreasonably. |
| Logs/Audit | Report-export requests remain diagnosable with report type, format, time window, grouping choice when relevant, freshness, and generation result. |

## Fixtures

- Seeded dashboard data with freshness metadata.
- Seeded funnel, source-performance, and content-effectiveness rows for at least
  one selectable reporting window.
- One unsupported report-and-format combination or invalid filter case for error
  proof.
- A reporting window with no matching records to prove export behavior on empty
  but valid results.

## Commands

```text
- ./scripts/verify-us-019.sh — planned story verification chain for report-export unit/integration coverage
- frontend/e2e/report-export.spec.ts — planned browser proof for reporting export flows
```

## Acceptance Evidence

- `tests/unit/test_report_export.py` — export validation, metadata, and CSV shaping
- `tests/integration/test_report_export_api.py` — export artifacts and unsupported-combination handling
- Reporting UI with export affordances and printable feedback
- `scripts/bin/harness-cli story verify US-019` — pass after the verify command is added
