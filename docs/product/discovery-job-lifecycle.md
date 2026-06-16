# Discovery Job Lifecycle

Source: `SPEC.md` sections 5.4, 7.2, 7.3, 11, 12, 14.1, and UC-01.

## Product Goal

Analysts need to launch a manual discovery run from a valid campaign and see a
trustworthy lifecycle for that run before LiveLead connects to live external
sources. The product contract must define how discovery jobs are created,
tracked, cancelled, retried, and explained, including how a structured campaign
or parsed natural-language brief turns into the snapshot that drives discovery.

## MVP Scope

This product slice covers:

- Manual discovery launch from a campaign.
- Snapshotting campaign criteria, target-market focus, and selected source
  context into the job record.
- Multi-source execution against deterministic mock connectors rather than live
  third-party systems.
- A stable job state model: `QUEUED`, `RUNNING`, `PARTIAL`, `SUCCEEDED`,
  `FAILED`, `CANCELLED`, and `NEEDS_USER_ACTION`.
- Progress updates that surface overall job progress and per-source progress to
  the UI.
- User-triggered cancellation for queued or running jobs.
- Controlled retry rules for transient failures and explicit non-infinite retry
  behavior for policy, authentication, or CAPTCHA-style failures.

Live external feed or API execution is defined in
  `docs/product/live-feed-and-api-discovery.md` (US-032). This lifecycle doc
  still does not cover:

- Scheduled or incremental live sync beyond the first recurrence slice defined
  in `docs/product/scheduled-discovery-and-sync.md`.
- Selenium or alternate-adapter connectors beyond the governed baseline in
  `docs/product/selenium-and-alternate-adapter-discovery.md` (US-034). Governed
  `Playwright` website discovery remains in
  `docs/product/public-website-playwright-discovery.md` (US-033).
- Full conversational discovery copilot. A prior brief may already have been
  parsed into campaign criteria, but live question-answer discovery guidance
  remains a follow-up slice.
- Full event-detail, ranking, or scoring UX.
- Interactive login or headed browser sessions. The first supervised session
  slice is defined in
  `docs/product/browser-session-console-and-isolation.md`.

## Contract Rules

- A discovery job can start only from a valid campaign and at least one allowed
  source selection.
- The job record must keep a criteria snapshot so later review can explain what
  inputs produced the run.
- When a campaign originated from a natural-language brief, the discovery
  snapshot should preserve the resolved criteria and important assumptions.
- Source policy must be checked before connector work begins, even in mock-run
  mode.
- Job progress must expose both aggregate progress and per-source progress.
- Cancellation must be available while the job is queued or running and must
  release worker resources.
- Transient network-style failures may retry with backoff, but policy-denied,
  authentication-required, or CAPTCHA-style states must not loop forever.
- Partial completion is valid when one source fails but other sources still
  return usable results.
- The product may reserve `NEEDS_USER_ACTION` even if the first implementation
  reaches it through deterministic fixtures rather than live login flows.

## API Surface

- `POST /campaigns/{id}/discovery-jobs`: create a manual discovery job from the
  current campaign and selected approved sources.
- `GET /discovery-jobs/{id}`: return job state, summary progress, per-source
  progress, and outcome metadata.
- `POST /discovery-jobs/{id}/cancel`: request cancellation for a queued or
  running job.
- Streaming updates must emit at least `job.started`, `job.progress`,
  `job.source_progress`, `job.needs_user_action`, `job.completed`, and
  `job.failed` through the chosen MVP transport.

## UI Surface

The user-facing slice should center on a manual run workflow:

- Review criteria and selected sources before launch.
- Show enough resolved criteria context that the user can understand what the
  discovery run is actually searching for.
- Start a discovery job from a campaign detail or equivalent run surface.
- See job status, aggregate progress, per-source progress, and error summaries.
- Cancel a queued or running job.
- See clear end states for success, partial success, failure, cancellation, and
  needs-user-action outcomes.

The UI does not need to claim full ranked event review in this story, but it
should make completion outcomes visible and understandable.

## Validation Implications

- Unit proof should cover job state transitions, retry rules, and snapshot
  creation.
- Integration proof should cover queue orchestration, policy checks before run,
  per-source progress persistence, and cancellation behavior.
- E2E proof should cover starting a manual discovery run, observing progress,
  and seeing terminal outcomes through deterministic mock connectors.
- Platform proof should keep backend worker, streaming, and frontend checks
  wired into the Harness matrix.
- Logs/audit proof should confirm denied and cancelled paths remain explainable.
