# Content Effectiveness And Attribution

Source: `SPEC.md` sections 5.9, 5.11, 5.12, and `AC-BIZ-09`.

## Product Goal

Owners, analysts, and sales users need to understand which content strategies
are correlated with useful lead outcomes rather than only which drafts were
generated or used. The product contract must define how LiveLead compares
content performance by content type, tone, and template metadata using approved
or used content plus linked lead outcomes, while keeping the first attribution
slice explainable and bounded before report-export workflows arrive.

## MVP Scope

This product slice covers:

- Showing content-effectiveness reporting for a selected time range.
- Grouping or comparing outcome-linked content by content type, tone, and
  prompt-template version or equivalent template metadata.
- Using used-content history and optional lead-outcome content links as the
  baseline attribution source.
- Showing freshness or last-updated metadata for the content-effectiveness read
  model.
- Showing explicit empty or unattributed states when outcome-linked content data
  is missing or incomplete in the selected window.

This product slice does not yet cover:

- Export workflows in CSV, PDF, HTML, or external systems. The first report-
  export slice is defined in `docs/product/report-export-and-printing.md`.
- Multi-touch attribution, weighted attribution, or causal claims.
- Revenue or ROI estimation.
- Automatic recommendation engines that rewrite future content strategy.
- External-channel analytics beyond what the product already records internally.

## Contract Rules

- Content-effectiveness metrics must derive from durable content metadata,
  handoff or used-state records, and explicit lead outcomes rather than guessed
  free-text associations.
- The first attribution slice must stay correlation-focused; it may compare
  linked outcomes across content groups, but it must not imply causal certainty.
- Outcome-linked content should be grouped only when the necessary metadata
  fields exist; incomplete records must be excluded or surfaced as unattributed.
- One selected time window must apply consistently across all comparisons in one
  response.
- Content-effectiveness reporting must expose freshness metadata and explicit
  empty or unattributed states when attribution data is incomplete.

## API Surface

- Content-effectiveness query or equivalent reporting endpoint with time-range
  and grouping input.
- Response payload that returns grouped content cohorts, linked outcome metrics,
  freshness metadata, and optional unattributed summaries.
- Validation errors that distinguish unsupported grouping keys from invalid date
  ranges without exposing storage internals.

## UI Surface

The MVP content-effectiveness slice should deepen the reporting area after
source performance:

- Content-effectiveness table or equivalent grouped comparison surface.
- Grouping controls for content type, tone, and template metadata.
- Metrics for used content volume and linked downstream outcomes when
  attributable.
- Freshness text and clear empty or unattributed states.

## Validation Implications

- Unit proof should cover grouping normalization, attribution rules, incomplete
  metadata handling, and freshness behavior.
- Integration proof should cover grouped reporting across content type, tone,
  and template metadata plus invalid-group handling.
- E2E proof should cover loading content-effectiveness reporting, switching
  group dimensions, and understanding empty or unattributed states.
- Logs or diagnostics should keep content-effectiveness queries explainable by
  time range, grouping key, freshness, and unattributed counts when present.
- Platform proof should keep the future content-effectiveness verification
  command wired into the Harness matrix before export stories build on it.
