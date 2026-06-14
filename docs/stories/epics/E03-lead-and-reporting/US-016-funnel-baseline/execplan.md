# Exec Plan

## Goal

Define and implement the first funnel reporting slice that shows the conversion
path from event to lead to contact to response to meeting to opportunity, uses
explicit cohort rules, and exposes freshness and unattributed-lead handling
before source-performance, content-effectiveness, or export stories arrive.

## Scope

In scope:

- Funnel report query and UI for a selected cohort or date range.
- Ordered steps for event, lead, contact, response, meeting, and opportunity.
- Explicit manual-lead or unattributed-lead handling.
- Freshness metadata and empty-state behavior.

Out of scope:

- Source-performance, campaign-comparison, or domain breakdowns.
- Content-effectiveness or attribution comparisons.
- Export workflows in CSV, PDF, HTML, or external systems.
- CRM-sync ingestion or automatic external outcome import.
- Revenue forecasting or advanced opportunity analytics.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.
- Cross-platform.

Hard gates:

- None directly, but the lane stays high-risk because this story introduces a
  new reporting contract across event, lead, and outcome data surfaces.

## Work Phases

1. Discovery: confirm funnel, freshness, and reporting dependencies from
   `SPEC.md`, `FR-REP-002`, `FR-REP-006`, `FR-LEAD-005`, and the documented
   outcome-tracking contract.
2. Design: define funnel cohort rules, step semantics, and manual-lead handling
   without widening into source-performance or export.
3. Validation planning: design proof for deterministic counts, empty states,
   unattributed-lead behavior, and funnel UI rendering.
4. Implementation: add funnel reporting query composition and the first funnel
   surface.
5. Verification: prove users can load the funnel and understand counts,
   freshness, and manual-lead caveats.
6. Harness update: leave a clean handoff for source-performance,
   content-effectiveness, and export stories.

## Stop Conditions

Pause for human confirmation if:

- Funnel semantics need weighted revenue or forecasting logic beyond the defined
  conversion steps.
- Source breakdowns or attribution comparisons start to creep into the same
  slice.
- The product needs CRM-driven conversion truth rather than manual MVP outcome
  data.
- Validation requirements need to weaken because cohort semantics are more
  ambiguous than one baseline slice can support safely.
