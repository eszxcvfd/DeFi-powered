# Design

## Domain Model

The story should formalize the first funnel-reporting read-model objects:

- `FunnelReport`: ordered funnel response for one selected cohort.
- `FunnelCohort`: normalized reporting window or cohort definition.
- `FunnelStep`: one ordered stage with label, count, and optional explanatory
  metadata.
- `UnattributedLeadSummary`: optional metadata for manual or event-unlinked
  leads that participate from the lead step onward.
- `FunnelFreshness`: last-updated metadata for the funnel read model.

Business rules:

- Funnel data must compose durable event, lead, and outcome records instead of
  inventing separate conversion facts.
- The first funnel slice must document a stable cohort rule; the UI and API
  should expose that rule clearly.
- Contact, response, meeting, and opportunity counts must derive from explicit
  outcome entries, not only from current lead stage.
- Manual leads must not silently inflate the event step; they should be excluded
  there or surfaced as unattributed context.
- Funnel counts should be deterministic for the same cohort and source data.

## Application Flow

- `GetFunnelReport` validates the requested cohort or date range, gathers
  event-linked lead records, composes downstream outcome counts, and returns an
  ordered step set with freshness metadata.
- Event and lead steps should document when different entity types are counted
  so users do not misread non-monotonic event-to-lead numbers.
- Outcome-backed steps should count leads that achieved at least one matching
  outcome within the cohort model defined by the story.
- Dashboard and future source-performance or export stories should reuse the
  funnel read-model definitions rather than reinterpret conversion steps.

## Interface Contract

Backend contract should minimally support:

- `GET /reports/funnel`
- Cohort or date-range input with predictable defaults and validation behavior.
- Ordered step payloads for event, lead, contact, response, meeting, and
  opportunity.
- Freshness metadata and optional unattributed-lead summary.

Expected payload concerns:

- Errors should distinguish invalid ranges from unsupported filters.
- Step keys and order must remain stable enough for later UI and export reuse.
- The response should explain cohort semantics and manual-lead handling without
  forcing users to infer them.

## Data Model

- Prefer a reporting read-model or query-layer composition over new operational
  transaction tables.
- Reuse canonical events, lead records, and explicit outcome entries as the
  underlying sources.
- Add lightweight derived metadata only when needed to explain cohort or
  unattributed-lead behavior.
- Preserve compatibility with later source-performance, content-effectiveness,
  and export reporting without reworking the funnel contract.

## UI / Platform Impact

- Add a funnel report surface or dashboard section with ordered step rendering.
- Add shared cohort or date-range controls aligned with reporting behavior.
- Show freshness text and unattributed context when relevant.
- Keep source breakdowns, attribution comparisons, and export controls visibly
  deferred.

## Observability

- Record diagnostic context for funnel queries, including cohort selection,
  ordered step counts, freshness, and unattributed-lead metadata.
- Keep enough structured evidence to explain why a step count changed when
  outcome or lead data changes underneath.

## Alternatives Considered

1. Derive the funnel only from current lead stages. Rejected because explicit
   outcome facts already exist and are the stronger source of truth for later
   conversion steps.
2. Defer funnel until source-performance and content-effectiveness also exist.
   Rejected because funnel is the next must-have reporting slice in the spec and
   now has enough durable data to stand on its own.
3. Include manual leads in the event step without distinction. Rejected because
   it would blur event-origin conversion meaning and make the report harder to
   trust.
