# Design

## Domain Model

The story should formalize the first report-export objects around existing
reporting slices:

- `ReportExportRequest`: selected report type, format, and current filter
  context.
- `ReportExportFormat`: supported export choices such as CSV and printable.
- `ReportExportArtifact`: generated file or equivalent artifact metadata for one
  export.
- `ReportExportMetadata`: report identity, selected time window, grouping
  context, freshness, and generated-at information.
- `UnsupportedReportExport`: validation outcome for unsupported report and format
  combinations.

Business rules:

- Export must reuse existing reporting queries and read models rather than
  recalculating metrics through a separate path.
- Export metadata must preserve enough context for users to understand what they
  are viewing outside the product.
- CSV output should shape stable rows and headers that map cleanly to the chosen
  report.
- Printable output should optimize readability and omit internal-only controls.
- The first slice stays synchronous or directly user-triggered; it does not
  widen into subscriptions or external delivery.

## Application Flow

- `ExportReport` validates report type, selected format, and current filters.
- The export flow reuses the current reporting query for dashboard, funnel,
  source-performance, or content-effectiveness, then maps the result into CSV or
  printable output.
- Export responses should carry artifact metadata that preserves time window,
  grouping choice when relevant, freshness, and generated-at context.
- Later delivery or sync stories should build on the same export contract without
  redefining report semantics.

## Interface Contract

Backend contract should minimally support:

- Report-export endpoint or equivalent download action.
- Stable input for report type, selected date range, grouping key when relevant,
  and export format.
- Predictable success and unsupported-format failure behavior.

Expected payload concerns:

- Errors should distinguish unsupported format combinations from invalid filters.
- Export metadata should be stable enough for later audit or artifact history.
- Grouped reports should preserve grouping labels and row ordering in exported
  output.

## Data Model

- Prefer generating export artifacts from the existing reporting read layer
  rather than creating new reporting-truth tables.
- Store only lightweight artifact metadata unless the implementation already has
  an artifact-storage pattern worth reusing.
- Keep compatibility with future asynchronous delivery or artifact-history
  stories without forcing them into this first slice.

## UI / Platform Impact

- Add export affordances to dashboard and grouped reporting views.
- Add format choices and download feedback.
- Keep current filter selections visible in the export flow.
- Preserve a clear distinction between report export and content export.

## Observability

- Record diagnostic context for report-export requests, including report type,
  format, selected window, grouping choice when relevant, freshness, and
  generation result.
- Keep enough structured evidence to diagnose when exported output differs from
  the interactive report view.

## Alternatives Considered

1. Add export separately inside each reporting feature. Rejected because the
   product needs one stable export contract across report surfaces.
2. Defer printable output and support only CSV first. Rejected because
   `FR-REP-005` explicitly requires CSV and PDF or HTML-printable export.
3. Reuse content-handoff export endpoints for report downloads. Rejected because
   report export has different source data, metadata, and user expectations.
