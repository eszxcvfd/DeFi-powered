# Design

## Domain Model

The story should formalize the first grouped source-reporting read-model
objects:

- `SourcePerformanceReport`: grouped reporting response for one selected time
  window.
- `SourceGrouping`: normalized grouping choice such as platform, connector,
  campaign, or industry.
- `SourcePerformanceRow`: one grouped result with metric values and explanatory
  metadata.
- `UnattributedSourceSummary`: optional metadata for records that cannot be
  assigned to the chosen grouping.
- `SourcePerformanceFreshness`: last-updated metadata for the grouped read
  model.

Business rules:

- Grouped metrics must compose durable source-linked event, lead, and outcome
  records rather than ad hoc frontend joins.
- Grouping keys must stay stable enough for later export and deeper reporting
  reuse.
- Records missing source linkage for the requested grouping must not silently
  inflate grouped rows; they should be excluded or surfaced as unattributed.
- One selected time window must govern every row and metric in the response.
- Product-level source performance must stay distinct from operational connector
  health metrics already handled in admin surfaces.

## Application Flow

- `GetSourcePerformanceReport` validates the selected time window and grouping
  key, gathers source-linked reporting records, computes grouped metrics, and
  returns grouped rows with freshness metadata.
- Grouped metrics should support at least discovered events, prioritized events,
  lead creation, and downstream outcome milestones when attributable.
- Dashboard, funnel, and later export stories should reuse these grouped keys
  rather than redefining source dimensions inconsistently.

## Interface Contract

Backend contract should minimally support:

- Source-performance reporting endpoint or equivalent grouped query.
- Time-range input and grouping selector with predictable defaults and
  validation behavior.
- Grouped rows with stable keys, metric values, freshness, and optional
  unattributed metadata.

Expected payload concerns:

- Errors should distinguish unsupported grouping keys from invalid date ranges.
- Group identifiers should be stable across UI refreshes and later export use.
- The response should make unattributed handling explicit when not every record
  can be grouped cleanly.

## Data Model

- Prefer a reporting read-model or query-layer composition over new operational
  transaction tables.
- Reuse canonical event source fields, campaign metadata, lead origin linkage,
  and explicit outcome records as the underlying attribution sources.
- Add lightweight derived metadata only when needed to explain grouped rows or
  unattributed records.
- Preserve compatibility with later content-effectiveness, export, and deeper
  attribution stories.

## UI / Platform Impact

- Add a grouped reporting surface for source performance.
- Add grouping controls for platform, connector, campaign, and industry.
- Show freshness text and unattributed context when relevant.
- Keep content attribution comparisons and export controls visibly deferred.

## Observability

- Record diagnostic context for source-performance queries, including time
  window, grouping key, grouped row count, freshness, and unattributed metrics.
- Keep enough structured evidence to explain why grouped metrics change when
  source-linked event, lead, or outcome data changes underneath.

## Alternatives Considered

1. Reuse connector admin health views as product performance reporting.
   Rejected because operational health and business effectiveness answer
   different questions.
2. Skip unattributed handling and report only fully linked rows. Rejected
   because users need visibility into what the grouped report leaves out.
3. Defer source performance until export exists. Rejected because grouped
   reporting provides product value on its own and should precede export.
