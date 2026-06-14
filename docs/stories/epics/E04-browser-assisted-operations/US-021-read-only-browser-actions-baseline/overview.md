# Overview

## Current Behavior

LiveLead can now open and supervise a governed browser session, but the session
is mostly passive after startup. Users still cannot trigger the first safe
read-only actions from the session console, and the product has no explicit
contract yet for action allowlists, selector guardrails, or action-level timeout
handling.

## Target Behavior

This story should establish the first read-only browser-action slice:

- Execute connector-allowlisted read-only actions inside an active session.
- Support a bounded first action set such as navigate, scroll, open detail, and
  read text.
- Show action lifecycle feedback in the browser session UI.
- Enforce selector resilience and timeout or budget guardrails.
- Prepare a clean handoff for later destructive confirmation, dry-run, and
  artifact stories.

## Affected Users

- Sales/BD users who need supervised read-only browser assistance before any
  external-side-effect workflow exists.
- Analysts who need to inspect source details inside a governed session.
- Admins and reviewers who need policy-safe visibility into allowed actions.

## Affected Product Docs

- `docs/product/browser-read-only-actions-and-guardrails.md`
- `docs/product/browser-session-console-and-isolation.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/source-registry-and-policy.md`

## Non-Goals

- Destructive or external-side-effect action confirmation.
- Dry-run preview for submit flows.
- Screenshot, console-log, or trace artifact retention.
- Browser profile lifecycle administration.
- CloakBrowser approval or outbound communication behavior.
