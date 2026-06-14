# Exec Plan

## Goal

Define and implement the first grouped content-effectiveness reporting slice
that compares content type, tone, and template metadata using used-content and
linked lead outcomes, exposes freshness and unattributed handling, and prepares
the way for report-export stories.

## Scope

In scope:

- Content-effectiveness grouped query and UI for a selected time range.
- Grouping by content type, tone, and template metadata.
- Attributable metrics for used content and linked downstream outcomes.
- Freshness metadata and unattributed-record handling.

Out of scope:

- Export workflows in CSV, PDF, HTML, or external systems.
- Revenue or ROI estimation.
- Multi-touch attribution or causal inference.
- Automatic recommendation engines for future content generation.
- External-channel analytics not already recorded in product data.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.
- Cross-platform.

Hard gates:

- None directly, but the lane stays high-risk because this story introduces a
  new grouped attribution contract across content, handoff, and lead-outcome
  data surfaces.

## Work Phases

1. Discovery: confirm content-effectiveness expectations from `SPEC.md`,
   `FR-REP-004`, and existing content and outcome contracts.
2. Design: define grouping semantics, attributable metrics, and unattributed
   handling without widening into export or optimization recommendations.
3. Validation planning: design proof for grouped metrics, invalid group keys,
   empty states, and unattributed behavior.
4. Implementation: add grouped content-effectiveness query composition and the
   first grouped reporting surface.
5. Verification: prove users can switch groupings and understand grouped
   metrics, freshness, and unattributed caveats.
6. Harness update: leave a clean handoff for export stories.

## Stop Conditions

Pause for human confirmation if:

- Content effectiveness needs revenue or ROI modeling beyond grouped counts.
- Export behavior or optimization recommendations start to creep into the same
  slice.
- The product needs external analytics or CRM-driven attribution truth rather
  than current durable product data.
- Validation requirements need to weaken because attribution semantics are more
  ambiguous than one baseline slice can support safely.
