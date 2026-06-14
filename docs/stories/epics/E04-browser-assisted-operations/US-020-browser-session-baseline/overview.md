# Overview

## Current Behavior

LiveLead already models browser-oriented connectors and keeps a placeholder
browser route in the UI, but users still cannot open a real supervised browser
session from an event or source. There is no first-class session record, no live
console that shows engine or URL state, and no safe stop control that closes the
session cleanly once the user is done supervising.

## Target Behavior

This story should establish the first browser-assisted session slice:

- Open a supervised browser session from a supported event or source entrypoint.
- Enforce isolated session context or governed profile boundaries.
- Show live session status in the UI, including engine, state, URL, runtime, and
  latest action.
- Allow the user to stop or close the session safely.
- Prepare a clean handoff for later allowlisted actions, confirmation flows, and
  browser artifact stories.

## Affected Users

- Sales/BD users who need a supervised browser workflow for source follow-up.
- Analysts who may need to inspect a source page in a governed session.
- Admins and reviewers who need policy-safe visibility into how sessions behave.

## Affected Product Docs

- `docs/product/browser-session-console-and-isolation.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/event-results-and-review.md`
- `docs/product/discovery-job-lifecycle.md`

## Non-Goals

- Executing allowlisted browser actions beyond session startup or stop.
- Confirmation tokens for destructive or external actions.
- Screenshot, console-log, or trace artifact retention.
- Browser profile lifecycle administration.
- CloakBrowser approval, browser-send, or outbound posting behavior.
