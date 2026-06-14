# Report Export And Printing

Source: `SPEC.md` sections 5.12, 7.2, 12, and `AC-BIZ-09`.

## Product Goal

Owners, analysts, sales users, and viewers need to take the reporting views they
already trust out of the product for review, sharing, and operational follow-up.
The product contract must define how LiveLead exports dashboard, funnel,
source-performance, and content-effectiveness reporting with stable filters,
freshness context, and explainable formatting, while keeping the first slice
bounded away from scheduled delivery or external-system synchronization.

## MVP Scope

This product slice covers:

- Exporting supported reporting views for the currently selected filters or time
  range.
- Supporting structured CSV export for report data that has stable tabular
  output.
- Supporting human-readable printable export through PDF or HTML-printable
  output for reporting views.
- Preserving report metadata such as selected time window, grouping choice when
  relevant, and freshness or generated-at context in exported output.
- Returning explicit errors when a report type or format combination is not
  supported in the current MVP slice.

This product slice does not yet cover:

- Scheduled report delivery, subscriptions, or digest email workflows.
- External-system export such as CRM, spreadsheet-sync, or cloud-drive push.
- Custom branding, templating, or presentation-layout editing.
- Bulk raw data export beyond the current report views.
- Revenue, ROI, or attribution semantics beyond what current reporting slices
  already define.

## Contract Rules

- Exported output must derive from the same reporting query inputs and durable
  read models as the on-screen report, not from a separate approximation path.
- Exported files must preserve enough metadata to explain what the user exported,
  including report identity, selected time window, and freshness or generated-at
  context.
- CSV output must stay structurally stable enough for spreadsheet use and
  downstream manual analysis.
- Printable output must remain readable without exposing internal-only controls
  or hidden operational metadata.
- Unsupported export combinations must fail clearly rather than silently
  returning incomplete files.
- The first export slice must stay user-triggered and read-only; it must not
  introduce scheduled jobs or outbound integrations.

## API Surface

- Report-export action or equivalent download endpoint that accepts report type,
  selected filters, and requested format.
- Response behavior that either returns an export artifact or a clear validation
  error for unsupported formats or invalid filters.
- Export metadata that identifies the report view, selected window, and freshness
  information included in the artifact.

## UI Surface

The MVP export slice should extend reporting after grouped reports exist:

- Export action on dashboard, funnel, source-performance, and
  content-effectiveness views.
- Format choices for CSV and printable output where supported.
- Clear loading, success, and unsupported-format feedback.
- Visible carry-through of current date range and grouping context so users know
  what will be exported.

## Validation Implications

- Unit proof should cover export-request validation, supported format mapping,
  metadata carry-through, and stable row shaping for CSV output.
- Integration proof should cover export responses for each supported report type
  plus unsupported-format and invalid-filter handling.
- E2E proof should cover exporting at least one grouped report and one summary
  report with the user's selected filters intact.
- Logs or diagnostics should keep export requests explainable by report type,
  format, time window, grouping choice when relevant, freshness, and artifact
  generation result.
- Platform proof should keep the future report-export verification command wired
  into the Harness matrix before scheduled-delivery or external-sync stories
  build on it.
