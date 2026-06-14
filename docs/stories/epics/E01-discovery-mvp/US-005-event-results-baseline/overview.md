# Overview

## Current Behavior

`US-004` gives LiveLead deterministic discovery-job lifecycle proof, but a
completed run still ends as a status update rather than a reviewable product
surface. The app has no canonical event contract, no durable provenance model,
no deduplication rules, and no minimal event list or detail experience for the
results a user just discovered.

## Target Behavior

The story should establish the first event-results slice after discovery:

- Normalize mock discovery output into canonical event records.
- Preserve source observations, provenance, and confidence for review.
- Deduplicate repeated findings across approved sources.
- Expose a minimal event results list for a campaign or selected discovery run.
- Expose a minimal event detail view with overview and source evidence.

This story makes discovery output reviewable. It does not yet claim scoring,
audience intelligence, engagement content, watchlist automation, or browser
session execution.

## Affected Users

- Analyst.
- Sales/BD.
- Viewer.
- Future scoring, engagement, and lead-workflow implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/discovery-job-lifecycle.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/event-results-and-review.md`

## Non-Goals

- Event scoring or score-breakdown UX.
- Audience hypothesis generation.
- Watchlist or reminder workflows.
- Browser-assisted event actions.
- CRM/export and lead conversion flows.
