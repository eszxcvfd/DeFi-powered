# Design

## Domain Model

The story should formalize the first content-attribution reporting read-model
objects:

- `ContentEffectivenessReport`: grouped comparison response for one selected
  time window.
- `ContentGrouping`: normalized grouping choice such as content type, tone, or
  template metadata.
- `ContentEffectivenessRow`: one grouped result with usage and outcome metrics
  plus explanatory metadata.
- `UnattributedContentSummary`: optional metadata for linked outcomes or used
  content that cannot be assigned to the chosen grouping.
- `ContentEffectivenessFreshness`: last-updated metadata for the grouped read
  model.

Business rules:

- Grouped effectiveness metrics must compose durable content metadata, used-state
  history, and explicit outcome links rather than ad hoc inference.
- Grouping keys must stay stable enough for later export and deeper attribution
  reuse.
- Records missing the required metadata or outcome linkage for the requested
  grouping must not silently inflate grouped rows; they should be excluded or
  surfaced as unattributed.
- One selected time window must govern every row and metric in the response.
- The first slice must describe correlation, not causation.

## Application Flow

- `GetContentEffectivenessReport` validates the selected time window and
  grouping key, gathers used-content and linked outcome records, computes
  grouped metrics, and returns grouped rows with freshness metadata.
- Grouped metrics should support at least used content volume and linked
  downstream outcomes when attributable.
- Source-performance and future export stories should reuse grouped keys and
  attribution semantics rather than redefining them inconsistently.

## Interface Contract

Backend contract should minimally support:

- Content-effectiveness reporting endpoint or equivalent grouped query.
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
- Reuse content generation metadata, approved or used-state history, and
  explicit outcome content links as the underlying attribution sources.
- Add lightweight derived metadata only when needed to explain grouped rows or
  unattributed records.
- Preserve compatibility with later export and deeper attribution stories.

## UI / Platform Impact

- Add a grouped reporting surface for content effectiveness.
- Add grouping controls for content type, tone, and template metadata.
- Show freshness text and unattributed context when relevant.
- Keep export controls visibly deferred.

## Observability

- Record diagnostic context for content-effectiveness queries, including time
  window, grouping key, grouped row count, freshness, and unattributed metrics.
- Keep enough structured evidence to explain why grouped effectiveness metrics
  change when linked content or outcome data changes underneath.

## Alternatives Considered

1. Compare content only by raw generation counts. Rejected because the story
   needs outcome-linked effectiveness, not draft volume alone.
2. Infer attribution from free-text notes without used-content or explicit
   outcome linkage. Rejected because the result would be too ambiguous to trust.
3. Defer content effectiveness until export exists. Rejected because grouped
   attribution provides product value on its own and should precede export.
