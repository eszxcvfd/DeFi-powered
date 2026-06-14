# Design

## Domain Model

The story should formalize the first supervised browser-session objects:

- `BrowserSession`: session aggregate with engine, state, source context, and
  lifecycle timestamps.
- `BrowserSessionTarget`: supported launch context such as event or source.
- `BrowserSessionStatus`: normalized status model for queued, starting, running,
  needs-user-action, failed, stopped, or completed states.
- `BrowserSessionTelemetry`: current URL, runtime, and latest-action summary
  exposed to the UI.
- `BrowserSessionIsolation`: metadata that explains which isolated context or
  governed profile boundary the session uses.

Business rules:

- Session creation must enforce policy and permission checks before worker-side
  browser startup.
- One user-visible session must map to one isolated browser context or governed
  profile boundary.
- The first slice should expose lifecycle status without widening into general
  action execution.
- Stop behavior must be explicit, idempotent where practical, and safe for
  worker resource cleanup.
- Session state must remain explainable through durable records and streaming
  status rather than transient UI guesses.

## Application Flow

- `CreateBrowserSession` validates the event or source launch context, checks
  current connector policy, selects the engine, allocates isolated session
  metadata, and asks the browser worker to start a supervised session.
- `GetBrowserSessionStatus` returns the latest durable session state plus runtime
  telemetry for UI display.
- `StopBrowserSession` marks a stop request, signals the worker, and closes the
  session cleanly when resources are released.
- Later action-execution and confirmation stories should reuse the same session
  identity and lifecycle model rather than redefining them.

## Interface Contract

Backend contract should minimally support:

- `POST /browser-sessions` for session creation from a supported source or event.
- `GET /browser-sessions/{id}` for live status reads.
- `POST /browser-sessions/{id}/stop` for safe stop requests.
- Streaming or equivalent updates for started and closed lifecycle changes.

Expected payload concerns:

- Errors should distinguish policy denial, invalid launch context, and
  unavailable engine/runtime failures.
- Session responses should include engine, state, URL when available, runtime,
  and latest-action summary without exposing raw secrets.
- Status fields should stay stable enough for later action, trace, and artifact
  stories.

## Data Model

- Prefer a durable browser-session table or equivalent persisted record rather
  than worker-memory-only state.
- Store launch context, engine, status, timestamps, latest URL, and isolation
  metadata needed for explanation and stop recovery.
- Reuse existing source-policy and event reference data instead of duplicating
  source truth.
- Keep room for later screenshots, traces, action history, or confirmation
  records without forcing them into this first slice.

## UI / Platform Impact

- Replace the browser placeholder route with the first supervised session
  surface.
- Add a launch affordance from a supported event or source entrypoint.
- Show engine, state, URL, runtime, and latest action in the session console.
- Add a stop control and visible terminal states.

## Observability

- Record diagnostics for session creation, start, stop, policy result, engine,
  launch target, and terminal outcome.
- Keep enough structured state to correlate UI launch requests with worker
  session lifecycle and safe-stop cleanup.

## Alternatives Considered

1. Start with full allowlisted browser actions in the first story. Rejected
   because session lifecycle and isolation need a stable baseline first.
2. Keep browser-session state only in worker memory. Rejected because the UI and
   audit path need durable, explainable session status.
3. Start with profile administration before a real session console exists.
   Rejected because profile lifecycle has lower product value before users can
   open and supervise a governed session.
