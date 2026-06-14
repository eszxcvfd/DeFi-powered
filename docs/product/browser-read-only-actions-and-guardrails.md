# Browser Read-Only Actions And Guardrails

Source: `SPEC.md` sections 5.10, 7.2, 7.3, 11, 14.2, and `UC-04`.

## Product Goal

Sales and analyst users need a safe way to do supervised, read-only browser
work once a governed session is already open. The product contract must define
how LiveLead executes connector-allowlisted actions such as navigate, scroll,
open detail, and read text through a stable adapter boundary, while enforcing
selector resilience, action status visibility, and timeout or budget guardrails
before destructive confirmation or debug-artifact stories widen scope.

## MVP Scope

This product slice covers:

- Executing connector-allowlisted read-only actions inside an existing browser
  session.
- Supporting a bounded first action set such as navigate, scroll, open detail,
  and read public text when connector policy allows them.
- Emitting action lifecycle status such as started and completed updates to the
  session UI.
- Enforcing selector resilience expectations that prefer semantic or stable
  locators over brittle absolute selectors.
- Enforcing timeout or budget guardrails for read-only browser actions.

This product slice does not yet cover:

- Destructive or external-side-effect actions that need explicit confirmation.
  Those behaviors are defined in
  `docs/product/browser-confirmation-and-preview.md`.
- Dry-run preview for submit actions.
- Screenshot, console-log, or trace retention artifacts.
- Browser profile administration.
- CloakBrowser approval or bulk communication workflows.

## Contract Rules

- A browser action may run only when it is present in the connector allowlist and
  the current session is in an eligible state.
- The first action slice must remain read-only; allowed actions may navigate,
  inspect, or reveal detail, but they must not submit forms, change account
  state, or send communication.
- Connectors should prefer semantic, role, label, or other stable locators, with
  brittle absolute selectors used only as a documented fallback.
- Each action must respect configured timeout and budget limits and fail safely
  when limits are exceeded.
- Browser action state must stay visible and explainable through status events
  and durable session history rather than silent background execution.
- CAPTCHA, MFA, or similar challenge states must stop execution or enter
  `NEEDS_USER_ACTION` rather than attempting bypass behavior.

## API Surface

- `POST /browser-sessions/{id}/actions`: execute an allowlisted read-only action
  against an active supervised session.
- Session status and action responses should expose action type, lifecycle state,
  summary result, and any needs-user-action outcome without leaking secrets.
- Streaming events or equivalent session updates should cover at least
  `browser.action_started` and `browser.action_completed`, with room for later
  `browser.confirmation_required` flows.

## UI Surface

The MVP read-only action slice should deepen the browser session console:

- Visible allowlisted action controls for the supported read-only action set.
- Action progress and latest-result feedback inside the browser session UI.
- Clear blocked or needs-user-action feedback when a requested action is not
  allowed or cannot proceed safely.
- Session status that stays coherent while actions run and complete.

## Validation Implications

- Unit proof should cover allowlist enforcement, selector-strategy preference,
  timeout or budget rules, and read-only action classification.
- Integration proof should cover action execution through the shared browser
  interface, action status persistence, and safe handling of CAPTCHA or
  needs-user-action states.
- E2E proof should cover launching a session, running supported read-only
  actions, and seeing action status updates in the UI.
- Logs or audit proof should confirm who ran which action, against which source
  or session, under what policy result, and with what terminal outcome.
- Platform proof should keep the future browser-action verification command wired
  into the Harness matrix before destructive confirmation or artifact stories
  build on it.
