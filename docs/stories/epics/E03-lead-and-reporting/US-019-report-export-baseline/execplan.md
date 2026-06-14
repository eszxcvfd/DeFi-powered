# Exec Plan

## Goal

Define and implement the first reporting-export slice that lets users export
dashboard and grouped reporting views as CSV plus printable output while
preserving selected filters, grouping context, and freshness metadata.

## Scope

In scope:

- Export actions for dashboard, funnel, source-performance, and
  content-effectiveness views.
- CSV export for supported report data.
- Printable export through PDF or HTML-printable output.
- Preservation of current time range, grouping choice when relevant, and
  freshness or generated-at metadata.
- Clear unsupported-format and invalid-filter handling.

Out of scope:

- Scheduled delivery, subscriptions, or digest emails.
- External-system sync or push export.
- Custom branding or template editing.
- Revenue or ROI modeling changes.
- New reporting metrics unrelated to export.

## Risk Classification

Risk flags:

- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.
- Cross-platform.

Hard gates:

- None directly, but the lane stays high-risk because this story adds a shared
  export contract across multiple reporting surfaces and user-visible download
  behavior.

## Work Phases

1. Discovery: confirm export requirements from `SPEC.md`, `FR-REP-005`, and
   current reporting and content-export contracts.
2. Design: define supported report and format combinations, metadata carry-
   through, and report-versus-content-export boundaries.
3. Validation planning: design proof for CSV shaping, printable output,
   unsupported combinations, and filter preservation.
4. Implementation: add the shared report-export backend flow and UI affordances
   on existing reporting surfaces.
5. Verification: prove exports reflect the selected report context and remain
   understandable outside the product.
6. Harness update: leave a clean handoff for scheduled-delivery or external-sync
   stories.

## Stop Conditions

Pause for human confirmation if:

- Export needs long-running background jobs, artifact retention policy, or
  asynchronous delivery beyond a direct user-triggered slice.
- The product needs custom branded templates or presentation editing in the same
  story.
- External-system synchronization starts to creep into the export baseline.
- Validation requirements need to weaken because exported output cannot be kept
  aligned with interactive reports safely.
