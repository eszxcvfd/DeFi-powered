# Overview

## Current Behavior

LiveLead now has a real external discovery baseline for official `API`/`RSS`/
`ICS` sources, but that still leaves an important gap: many event and
livestream pages exist only on public websites with modern DOM flows. The
project already has separate supervised browser-session and read-only action
contracts, yet there is no discovery-specific product contract or story packet
for running governed `Playwright` website recipes automatically inside the
discovery job workflow.

## Target Behavior

This story should establish the first public-website discovery slice for
LiveLead:

- Run approved public-website connectors through a `Playwright` adapter from
  the existing manual discovery-job workflow.
- Support a bounded browser recipe contract for wait rules, locators,
  pagination/scroll, extraction fields, budgets, and optional snapshots.
- Turn extracted website data into canonical events and source observations that
  appear in the existing event review surfaces.
- Preserve per-source progress, partial success, and `NEEDS_USER_ACTION` or
  blocked states when a website challenges automation or becomes unstable.
- Keep browser discovery as a fallback behind official feed/API preference, not
  a replacement for the broader governance model.

This story should deliver the `Playwright` part of the discovery acceptance path
without folding in Selenium, manual browser session UX, or destructive browser
actions.

## Affected Users

- Analysts who need real event discovery from public websites when feeds/APIs do
  not exist.
- Owners/Admins who govern which website connectors are runnable and need clear
  policy or recipe blocked states.
- Future implementation agents extending Selenium discovery and richer connector
  health/reporting on top of a stable browser-recipe baseline.

## Affected Product Docs

- `docs/product/source-registry-and-policy.md`
- `docs/product/live-feed-and-api-discovery.md`
- `docs/product/public-website-playwright-discovery.md`
- `docs/product/platform-and-automation-policy.md`

## Non-Goals

- Selenium or alternate adapter discovery.
- Interactive login or saved browser-state reuse.
- Manual browser-session console workflows.
- Confirmation-gated browser actions or external-side-effect actions.
- Full recipe-builder UI or connector-health analytics dashboard.
