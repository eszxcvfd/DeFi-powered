# Exec Plan

## Goal

Define and implement the first grouped source-performance reporting slice that
compares platform, connector, campaign, and industry performance using durable
source-linked records, exposes freshness and unattributed handling, and prepares
the way for content-effectiveness and export stories.

## Scope

In scope:

- Source-performance grouped query and UI for a selected time range.
- Grouping by platform, connector, campaign, and industry.
- Attributable metrics for source-linked events, prioritized events, leads, and
  downstream outcomes when supported.
- Freshness metadata and unattributed-record handling.

Out of scope:

- Content-effectiveness comparisons or attribution by template or tone.
- Export workflows in CSV, PDF, HTML, or external systems.
- Revenue or ROI estimation.
- Connector-health operations dashboards.
- CRM-synced multi-touch attribution.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.
- Cross-platform.

Hard gates:

- None directly, but the lane stays high-risk because this story introduces a
  new grouped reporting contract across discovery, event, lead, and outcome
  data surfaces.

## Work Phases

1. Discovery: confirm source-performance dimensions and freshness expectations
   from `SPEC.md`, `FR-REP-003`, and existing reporting contracts.
2. Design: define grouping semantics, attributable metrics, and unattributed
   handling without widening into content-effectiveness or export.
3. Validation planning: design proof for grouped metrics, invalid group keys,
   empty states, and unattributed behavior.
4. Implementation: add grouped source-performance query composition and the
   first grouped reporting surface.
5. Verification: prove users can switch groupings and understand grouped
   metrics, freshness, and unattributed caveats.
6. Harness update: leave a clean handoff for content-effectiveness and export
   stories.

## Stop Conditions

Pause for human confirmation if:

- Source performance needs revenue or ROI modeling beyond grouped counts.
- Content-effectiveness or export behavior starts to creep into the same slice.
- The product needs CRM-driven attribution truth rather than current durable
  source-linked product data.
- Validation requirements need to weaken because grouping semantics are more
  ambiguous than one baseline slice can support safely.
