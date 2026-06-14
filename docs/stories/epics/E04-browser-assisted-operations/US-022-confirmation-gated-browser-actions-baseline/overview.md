# Overview

## Current Behavior

LiveLead can now run allowlisted read-only actions in a supervised browser
session, but any action with external side effects is still out of bounds.
Users do not yet have a preview or dry-run surface for submit-like actions, no
explicit confirmation step is defined, and there is no durable audit contract
for approve or cancel decisions around those actions.

## Target Behavior

This story should establish the first confirmation-gated browser-action slice:

- Preview or dry-run destructive or external-side-effect actions before
  execution.
- Require explicit confirm or cancel decisions for those actions.
- Scope confirmation to one requested action in one session.
- Show confirmation-required, confirmed, cancelled, and completed states in the
  browser session UI.
- Preserve audit context for request, confirmation, cancellation, and execution.

## Affected Users

- Sales/BD users who need supervised action execution without unsafe implicit
  automation.
- Analysts or reviewers who need confidence that side-effect actions stay
  governed and explainable.
- Admins and compliance-minded operators who need auditable confirmation
  boundaries.

## Affected Product Docs

- `docs/product/browser-confirmation-and-preview.md`
- `docs/product/browser-read-only-actions-and-guardrails.md`
- `docs/product/browser-session-console-and-isolation.md`
- `docs/product/platform-and-automation-policy.md`

## Non-Goals

- Screenshot, console-log, or trace retention artifacts.
- Browser profile lifecycle administration.
- CloakBrowser approval workflow.
- Bulk autonomous outbound communication.
- Replacing explicit human confirmation with standing approval.
