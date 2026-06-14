# Overview

## Current Behavior

`US-002` gives LiveLead campaign setup and `US-003` gives source governance, but
the product still has no durable discovery-job contract. Users cannot yet launch
a manual discovery run, the queue or worker lifecycle is not described in a
story packet, and there is no defined progress or cancellation behavior to prove
before integrating live connectors.

## Target Behavior

The story should establish the first manual discovery lifecycle slice:

- Launch a discovery job from a valid campaign using deterministic mock
  connectors only.
- Snapshot criteria and source context into the job record.
- Drive stable job states, progress, partial-success, failure, cancellation, and
  needs-user-action outcomes.
- Stream progress updates to the UI and expose terminal job status through the
  API.
- Enforce source policy before any mock connector run begins.

This story proves orchestration, not real-world data collection. Live API, RSS,
Playwright, and Selenium execution remain follow-on work after the lifecycle and
proof ladder exist.

## Affected Users

- Analyst.
- Owner/Admin.
- Future discovery, event, and browser-operation implementation agents.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/campaign-and-icp.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/discovery-job-lifecycle.md`

## Non-Goals

- Live third-party connector execution.
- Full event-detail or ranked-results workflows.
- Scheduled jobs or cron management.
- AI query expansion.
- Interactive authentication or headed browser sessions.
