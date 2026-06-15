# Browser Session Console And Isolation

Source: `SPEC.md` sections 5.10, 7.2, 7.3, 11, 14.2, and `UC-04`.

## Product Goal

Sales and analyst users need a supervised browser-assisted workflow that lets
them open a governed session from an event or source when API or feed workflows
are not sufficient. The product contract must define how LiveLead starts an
isolated browser session, exposes live session state in the UI, and lets the
user stop the session safely, while keeping action execution, destructive
confirmation, profile administration, and debug artifacts for later slices.
This is a supporting capability for the core MVP jobs in
`docs/product/mvp-scope-and-priorities.md`, not a separate primary product
track.

## MVP Scope

This product slice covers:

- Opening a browser session from a supported event or source entrypoint in the
  UI.
- Enforcing isolated browser context or profile handling for each session based
  on current connector and workspace policy.
- Showing live session status, including engine, session state, current URL,
  runtime, and latest action summary.
- Allowing the user to stop or close an in-progress session safely.
- Emitting the baseline session lifecycle signals needed for UI status updates.

This product slice does not yet cover:

 - Executing allowlisted browser actions beyond the minimal session start or stop
  lifecycle. Those behaviors are defined in
  `docs/product/browser-read-only-actions-and-guardrails.md`.
- Destructive or external action confirmation tokens and submit workflows.
- Screenshot, console-log, or trace artifact retention.
- Browser profile administration such as create, lock, expire, or delete.
- CloakBrowser enablement, compliance approval workflow, or browser-send
  automation.

## Contract Rules

- A browser session may start only from an allowed source or connector and must
  pass current policy and permission checks before worker execution begins.
- Each session must run in an isolated browser context or governed profile
  boundary rather than sharing mutable browsing state across users silently.
- Session state shown in the UI must expose enough information for supervised
  usage: engine, state, current URL when available, runtime, and latest action.
- Users must be able to stop a queued or running browser session, and the stop
  flow must release worker-side browser resources safely.
- Browser-session status must stay explainable through durable state or streaming
  events rather than hidden worker-only memory.
- The first slice must remain read-only at the action layer; opening a session
  does not imply that form submission, messaging, or account-changing actions are
  allowed yet.

## API Surface

- `POST /browser-sessions`: create a supervised browser session for a supported
  event or source context.
- `GET /browser-sessions/{id}`: return current session status, engine,
  URL/runtime metadata, and latest-action summary.
- `POST /browser-sessions/{id}/stop`: request a safe stop for a queued or
  running session.
- Streaming events or equivalent status updates should cover at least
  `browser.session_started` and `browser.session_closed`, with room for later
  action-state events.

## UI Surface

The MVP browser-session slice should introduce the first supervised console:

- Launch browser session action from a supported source or event workflow.
- Browser session console or detail view that shows engine, state, current URL,
  runtime, and latest action.
- Clear loading, running, stopped, failed, and needs-user-action states.
- Stop session control with visible feedback when shutdown is in progress or
  complete.

## Validation Implications

- Unit proof should cover session-state transitions, isolation metadata rules,
  and stop eligibility.
- Integration proof should cover policy-gated session creation, status reads,
  worker stop behavior, and adapter lifecycle cleanup.
- E2E proof should cover opening a session from the UI, watching live status,
  and stopping it safely.
- Logs or audit proof should confirm who opened and stopped a browser session,
  for which source or event, under which engine and policy result.
- Platform proof should keep the future browser-session verification command
  wired into the Harness matrix before action-execution, confirmation, or
  profile-management stories build on it.
