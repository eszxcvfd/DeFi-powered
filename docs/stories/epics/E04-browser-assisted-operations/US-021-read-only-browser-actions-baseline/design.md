# Design

## Domain Model

The story should formalize the first supervised browser-action objects:

- `BrowserActionRequest`: requested action type plus bounded parameters for an
  active session.
- `BrowserActionType`: supported read-only actions such as navigate, scroll,
  open detail, and read text.
- `BrowserActionPolicy`: connector-derived allowlist and classification rules for
  one session.
- `BrowserActionResult`: lifecycle state, summary outcome, and optional
  needs-user-action or limit-hit metadata.
- `BrowserLocatorStrategy`: ordered locator preference that favors semantic or
  stable selectors before brittle fallbacks.

Business rules:

- Action execution must enforce the connector allowlist before any browser engine
  call occurs.
- The first slice supports read-only actions only; submit, post, or account-
  mutating actions remain blocked or deferred.
- Action execution must update session-visible lifecycle state so users can see
  what is happening.
- Selector strategy should favor semantic or stable locators and keep brittle
  fallbacks explicit.
- Timeout and budget enforcement must stop runaway read-only automation safely.

## Application Flow

- `ExecuteBrowserAction` validates the session state, checks the connector
  allowlist, normalizes action parameters, and invokes the shared browser
  adapter interface.
- The browser worker emits action lifecycle updates and persists action outcome
  summaries so the session UI stays synchronized.
- Challenge or unsafe states should return `NEEDS_USER_ACTION` or a blocked
  outcome rather than bypass behavior.
- Later confirmation and dry-run stories should reuse the same action identity,
  policy checks, and lifecycle model.

## Interface Contract

Backend contract should minimally support:

- `POST /browser-sessions/{id}/actions` for allowlisted read-only actions.
- Stable request and response shapes for action type, parameters, lifecycle
  state, and summarized result.
- Streaming or equivalent session updates for started and completed action
  events.

Expected payload concerns:

- Errors should distinguish unsupported action type, blocked policy, invalid
  session state, and timeout or budget failure.
- Responses should expose enough result detail for the UI without leaking raw
  secrets or protected browser internals.
- Action records should stay stable enough for later confirmation, artifact, and
  audit stories.

## Data Model

- Prefer durable action-history or session-linked action records over UI-only
  transient state.
- Store action type, normalized parameters, lifecycle timestamps, policy result,
  and summarized outcome.
- Reuse session identity and source-policy metadata instead of duplicating
  browser governance data.
- Leave room for later confirmation tokens, artifacts, or richer trace links
  without forcing them into this first action slice.

## UI / Platform Impact

- Add read-only action controls to the browser session console.
- Show action progress, success, blocked, timeout, and needs-user-action
  feedback.
- Keep the session UI coherent while actions run and update latest-action state.
- Preserve a clear distinction between read-only and external-side-effect actions.

## Observability

- Record diagnostics for action request type, connector allowlist result,
  selector strategy choice, timeout or budget outcome, and final lifecycle
  state.
- Keep enough structured evidence to correlate session creation, action
  execution, and later confirmation-gated actions.

## Alternatives Considered

1. Jump straight to destructive confirmation flows. Rejected because the product
   needs a safe read-only action baseline first.
2. Allow any connector-defined action without a shared policy gate. Rejected
   because browser automation needs a stable governance boundary.
3. Treat selector strategy as an engine-only detail. Rejected because resilience
   is part of the product contract and proof surface.
