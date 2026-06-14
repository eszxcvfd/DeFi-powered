# Design

## Domain Model

The story should formalize discovery lifecycle concepts around a deterministic
run model:

- `DiscoveryJob`: organization-scoped run record linked to a campaign.
- `criteria_snapshot`: immutable snapshot of campaign filters and selected
  sources used for the run.
- `DiscoverySourceRun` or equivalent per-source progress model: source id,
  current state, items found, pages processed, last error, and timing metadata.
- `JobOutcome`: terminal status plus summary counts and failure context.
- `CancellationRequest` or equivalent worker signal for queued/running jobs.

Business rules:

- A job may start only when the campaign exists and at least one selected source
  passes policy evaluation.
- A job records the selected inputs before worker execution starts.
- `PARTIAL` is valid when at least one source succeeds and at least one fails.
- `NEEDS_USER_ACTION` is reserved for auth/challenge-style conditions even in
  mock mode.
- Cancellation must win over further work once acknowledged by the worker.

## Application Flow

Commands:

- Create manual discovery job.
- Start job execution in the worker.
- Report source progress.
- Mark needs-user-action outcome.
- Cancel discovery job.

Queries:

- Get discovery job detail and current progress.
- Stream job progress events to the UI.
- List recent jobs per campaign if needed for the run surface.

Handlers should keep queue, transport, and mock-connector details in
infrastructure/application layers rather than domain code. Source-policy
evaluation should happen before a source run is scheduled.

## Interface Contract

The minimum contract should cover:

- `POST /campaigns/{id}/discovery-jobs` for job creation.
- `GET /discovery-jobs/{id}` for status and progress snapshots.
- `POST /discovery-jobs/{id}/cancel` for cancellation.
- Streaming events that emit at least `job.started`, `job.progress`,
  `job.source_progress`, `job.needs_user_action`, `job.completed`, and
  `job.failed`.

Responses should expose stable job states, progress summaries, and source-level
outcomes without leaking infrastructure internals. Error contracts should
distinguish invalid campaign state, policy-denied start, missing job, and
already-terminal cancellation attempts.

## Data Model

Expected persistence work:

- Add discovery job storage with campaign reference, criteria snapshot, status,
  progress payload, timestamps, and initiator metadata.
- Add per-source progress or outcome storage if the progress payload alone is
  not enough for reliable streaming and retries.
- Preserve idempotency or duplicate-run protection for retry scenarios.
- Keep event/result persistence minimal and deterministic in this story; only
  store what the lifecycle proof needs before later event-domain stories expand
  the model.

## UI / Platform Impact

- Add a manual run surface from campaign context.
- Add progress visualization with overall and per-source state.
- Add user-triggered cancellation.
- Keep results presentation intentionally lightweight; this story is about run
  lifecycle rather than full ranked event review.
- Choose an MVP progress transport compatible with the current frontend/backend
  stack without locking future richer streaming behavior out.

## Observability

- Record structured job lifecycle transitions and per-source outcome summaries.
- Make policy-denied, cancelled, failed, partial, and needs-user-action paths
  diagnosable.
- Ensure cleanup events or equivalent traces exist for terminal and cancelled
  flows so worker/resource release can be verified.

## Alternatives Considered

1. Skip mock connectors and wait for live sources before proving the queue
   lifecycle. Rejected because that would blur orchestration bugs with
   third-party variability.
2. Make discovery synchronous in the API for the first cut. Rejected because it
   would bypass the queue/worker behavior the MVP already commits to.
