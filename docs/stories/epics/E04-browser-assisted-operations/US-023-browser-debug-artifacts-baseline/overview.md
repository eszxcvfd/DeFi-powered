# Overview

## Current Behavior

LiveLead can now open supervised browser sessions, run allowlisted read-only
actions, and gate side-effect actions behind preview and confirmation. The
product still has no first governed debug-artifact slice: users cannot take a
manual screenshot from the session console, console logs and traces are not
defined as retained artifacts, and there is no retention or access contract for
session-level browser debugging data.

## Target Behavior

This story should establish the first browser debug-artifact slice:

- Enable governed debug capture for supervised browser sessions.
- Allow manual screenshot capture from the browser session UI when policy
  permits.
- Capture console-log and trace artifacts only when debug mode is enabled.
- Expose artifact availability and retrieval through durable metadata and
  authorized UI access.
- Enforce retention and expiration rules without leaking secrets or widening
  browser action permissions.

## Affected Users

- Sales/BD users who need screenshot evidence while supervising a browser flow.
- Analysts who need console-log or trace artifacts to diagnose connector or DOM
  issues.
- Admins and compliance-minded operators who need retention and access control
  over potentially sensitive browser artifacts.

## Affected Product Docs

- `docs/product/browser-debug-artifacts-and-retention.md`
- `docs/product/browser-session-console-and-isolation.md`
- `docs/product/browser-read-only-actions-and-guardrails.md`
- `docs/product/browser-confirmation-and-preview.md`
- `docs/product/platform-and-automation-policy.md`

## Non-Goals

- Browser profile lifecycle administration.
- CloakBrowser approval workflow.
- Broad forensic capture such as continuous video recording or HAR archives.
- Exporting cookies, storage state, or other secret-bearing browser state.
- Replacing audit and confirmation rules with unrestricted debug access.
