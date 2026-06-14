# Exec Plan

## Goal

Define and implement the first reporting dashboard slice that summarizes
existing product workflow metrics for a chosen time range, shows freshness on
every widget, and clearly distinguishes empty values from unavailable metrics
before funnel, source-performance, or export stories arrive.

## Scope

In scope:

- Dashboard overview query and UI for a selected time range.
- Summary widgets backed by durable current workflow data.
- Per-widget freshness or last-updated metadata.
- Explicit empty and unavailable metric states.

Out of scope:

- Funnel visualization and conversion-step reporting.
- Source-performance or campaign-comparison reports.
- Content-effectiveness analysis.
- CSV, PDF, printable, or CRM export behavior.
- New watchlist or outcome-entry workflows added only for reporting.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.
- Cross-platform.

Hard gates:

- None directly, but the lane stays high-risk because this story introduces a
  new user-visible reporting contract across event, content, lead, and reminder
  data surfaces.

## Work Phases

1. Discovery: confirm dashboard metric, freshness, and reporting boundaries from
   `SPEC.md`, `FR-REP-001`, `FR-REP-006`, and `AC-BIZ-09`.
2. Design: define overview widgets, availability states, and freshness behavior
   without widening into funnel or export.
3. Validation planning: design proof for time-window rules, cross-domain
   aggregation, explicit unavailable states, and dashboard UI rendering.
4. Implementation: add reporting query composition and the first dashboard
   overview surface.
5. Verification: prove users can load the dashboard, switch time windows, and
   understand both populated and unavailable widgets.
6. Harness update: leave a clean handoff for funnel, source-performance, and
   export stories.

## Stop Conditions

Pause for human confirmation if:

- The story needs new operational data-entry workflows only to satisfy one
  metric.
- Funnel visualization or export behavior starts to creep into the same slice.
- Reporting requirements need guessed values instead of durable source data.
- Validation requirements need to weaken because cross-domain aggregation
  changes more surfaces than expected.
