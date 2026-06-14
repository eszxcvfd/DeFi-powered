# Overview

## Current Behavior

`US-005` defines canonical event review, provenance, and deduplication, but
LiveLead still leaves users with a flat list of events instead of a prioritized
queue. Campaign scoring weights exist from `US-002`, yet no score record,
priority mapping, re-score action, or explainable ranking surface turns those
weights into usable decisions.

## Target Behavior

This story should establish the first scoring slice after event review:

- Calculate a campaign-aware score for canonical events.
- Derive a priority level from configurable thresholds.
- Persist versioned score results with effective weights and calculation time.
- Expose score summary in event results.
- Expose score breakdown and explicit re-score behavior in event detail.

This story makes event review actionable. It does not yet claim full audience
hypothesis workflows, engagement-plan generation, content approval, or lead
pipeline actions.

## Affected Users

- Analyst.
- Sales/BD.
- Viewer.
- Future audience, engagement, and lead-workflow implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/campaign-and-icp.md`
- `docs/product/event-results-and-review.md`
- `docs/product/event-scoring-and-priority.md`

## Non-Goals

- Full audience-hypothesis generation and feedback workflows.
- AI-generated engagement-plan or content workflows.
- Bulk re-score or multi-event comparison.
- Watchlist, reminder, or lead conversion behavior.
- Browser-assisted actions from event detail.
