# Design

## Domain Model

The story should formalize the first confirmation-aware browser-action objects:

- `ConfirmationGatedBrowserAction`: side-effect action request tied to one
  session and one intended effect.
- `BrowserActionPreview`: preview or dry-run summary presented before execution.
- `BrowserConfirmationState`: pending, confirmed, cancelled, expired, blocked,
  or executed state for the action request.
- `BrowserConfirmationDecision`: actor, time, and decision metadata for confirm
  or cancel outcomes.
- `BrowserConfirmationAuditContext`: durable context that links request,
  decision, and execution result.

Business rules:

- Side-effect actions must be classified before execution so the system knows
  confirmation is required.
- One preview and confirmation flow must map to one concrete requested action;
  approval cannot silently roll over to later unrelated actions.
- Confirm and cancel behavior must be idempotent where practical and safe under
  retries or repeated UI clicks.
- Dry-run or preview output must stay aligned with the executable action
  parameters so the user reviews what will actually happen.
- Expired, cancelled, or blocked confirmation requests must never execute the
  side-effect action.

## Application Flow

- `RequestConfirmationGatedAction` validates the session and action type,
  classifies the action as confirmation-required, and returns preview or dry-run
  output with pending-confirmation state.
- `ConfirmBrowserAction` records the actor decision, checks the request is still
  valid, and invokes the shared browser adapter for execution.
- `CancelBrowserAction` records cancellation and closes the confirmation request
  without executing the side effect.
- Existing session and action lifecycle updates should extend to carry
  confirmation-required, confirmed, cancelled, and executed states.

## Interface Contract

Backend contract should minimally support:

- Confirmation-required extension of `POST /browser-sessions/{id}/actions`.
- Confirm and cancel actions or equivalent state-transition endpoints.
- Stable preview, confirmation-state, and execution-outcome payloads.

Expected payload concerns:

- Errors should distinguish unsupported side-effect actions, expired or invalid
  confirmation requests, and policy-blocked execution.
- Responses should expose enough preview detail for user judgment without
  leaking sensitive secrets.
- Confirmation state should remain stable enough for later artifact and
  compliance stories.

## Data Model

- Prefer durable session-linked confirmation records over UI-only ephemeral
  tokens.
- Store action type, normalized parameters, preview summary, confirmation state,
  actor decisions, and final outcome metadata.
- Reuse session identity and browser-action policy context rather than
  duplicating session governance data.
- Leave room for later artifact references, richer retention rules, or approval
  policy extensions without forcing them into this first slice.

## UI / Platform Impact

- Add preview UI for confirmation-gated actions in the browser session console.
- Add confirm and cancel controls with clear state feedback.
- Keep read-only actions visually distinct from side-effect actions.
- Preserve session coherence while confirmation is pending or resolved.

## Observability

- Record diagnostics for action classification, preview generation,
  confirmation-required state, actor decisions, and execution outcome.
- Keep enough structured evidence to correlate the preview the user saw with the
  action that was later confirmed or cancelled.

## Alternatives Considered

1. Allow side-effect actions after a generic one-time session approval. Rejected
   because confirmation must stay scoped to each concrete action.
2. Skip preview and ask only for yes/no confirmation. Rejected because the user
   needs to understand the intended effect before approving it.
3. Defer all side-effect actions until artifacts and profiles are built.
   Rejected because confirmation-gated execution is a core browser workflow in
   the current spec.
