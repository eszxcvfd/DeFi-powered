# Browser Confirmation And Preview

Source: `SPEC.md` sections 5.10, 7.2, 7.3, 11, 14.2, and `UC-04`.

## Product Goal

Sales and analyst users need a safe way to handle browser actions that could
change external state once supervised sessions and read-only actions already
exist. The product contract must define how LiveLead previews or dry-runs
destructive or external-side-effect actions, requires explicit confirm or cancel
decisions before execution, and preserves audit context for those decisions,
while keeping artifact retention, profile lifecycle, and CloakBrowser approval
for later slices.
This confirmation layer is a safeguard for the core MVP jobs in
`docs/product/mvp-scope-and-priorities.md`; it is not a license for autonomous
outreach or a new primary workflow.

## MVP Scope

This product slice covers:

- Classifying browser actions that require confirmation because they could submit
  a form, register an event, save account state, or send communication.
- Showing a preview or dry-run summary of the requested side-effect action
  before execution.
- Requiring an explicit confirm or cancel decision immediately before execution.
- Emitting confirmation-required and post-confirmation action status updates to
  the session UI.
- Preserving audit or durable status context for who requested, confirmed,
  cancelled, or executed the side-effect action.

This product slice does not yet cover:

- Screenshot, console-log, or trace retention artifacts.
- Browser profile administration.
- CloakBrowser approval workflow.
- Bulk or autonomous outbound communication.
- Broad workflow automation beyond one supervised, explicitly confirmed action at
  a time.

## Contract Rules

- Any browser action classified as destructive, account-changing, or externally
  visible must require preview and explicit confirmation before execution.
- The preview surface must summarize the intended target and effect clearly
  enough for a human to approve or cancel safely.
- The first dry-run slice may simulate or summarize the action without executing
  the external side effect, but it must stay consistent with the eventual
  executable action contract.
- Confirmation must be scoped to the exact requested action and session context;
  one confirmation must not implicitly authorize unrelated future actions.
- Cancelled or expired confirmation requests must not execute the side-effect
  action.
- Confirmation and execution status must remain explainable through durable
  action state and audit context rather than transient UI memory.

## API Surface

- Confirmation-aware browser action request or equivalent extension of
  `POST /browser-sessions/{id}/actions` for side-effect actions.
- Response or follow-up flow that can return preview data, confirmation-required
  state, confirm/cancel decisions, and final execution outcome.
- Streaming events or equivalent session updates should cover at least
  `browser.confirmation_required` plus the existing action lifecycle events.

## UI Surface

The MVP confirmation slice should deepen the browser session console after
read-only actions:

- Preview UI for side-effect actions with clear target and impact summary.
- Confirm and cancel controls tied to one requested action.
- Visible pending-confirmation, confirmed, cancelled, blocked, and completed
  states.
- Clear distinction between safe read-only actions and confirmation-gated
  actions.

## Validation Implications

- Unit proof should cover action classification, confirmation-token scoping,
  cancel behavior, and preview or dry-run consistency rules.
- Integration proof should cover confirmation-required API behavior, confirm or
  cancel transitions, and audit-context persistence for side-effect actions.
- E2E proof should cover requesting a confirmation-gated action, reviewing the
  preview, confirming or cancelling, and seeing the resulting session state.
- Logs or audit proof should confirm who requested, confirmed, cancelled, or ran
  a side-effect browser action and against which session or source.
- Platform proof should keep the future confirmation verification command wired
  into the Harness matrix before artifact-retention or profile-management
  stories build on it.
