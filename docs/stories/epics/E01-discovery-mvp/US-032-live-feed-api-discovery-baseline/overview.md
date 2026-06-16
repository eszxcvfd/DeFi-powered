# Overview

## Current Behavior

LiveLead already supports campaign setup, governed source registry, manual
discovery-job orchestration, canonical event review, watchlists, and manual
event correction. However, discovery is still not finding real external events
from approved platforms the way users expect. The current lifecycle contract
stops at deterministic mock connectors, and while parts of the runtime can read
feed-style URLs, there is no dedicated product contract or proof ladder for
policy-aware live external `API`/`RSS`/`ICS` discovery.

## Target Behavior

This story should establish the first real external discovery slice for
LiveLead:

- Run approved live `API`, `RSS`, `Atom`, `sitemap`, or `ICS` connectors from
  the existing manual discovery-job workflow.
- Turn live connector output into canonical events and source observations that
  appear in the existing event results and detail surfaces.
- Preserve per-source progress, partial success, denied states, and
  needs-user-action outcomes when a live source is misconfigured or requires
  interaction.
- Keep official feeds and APIs as the preferred path before any browser-driven
  connector work.
- Expose enough readiness and failure context that admins and analysts can tell
  whether a live source is runnable and what blocked it.

This story should deliver real-source value without jumping ahead to Playwright,
Selenium, delegated-auth platform APIs, or scheduled synchronization.

## Affected Users

- Analysts who expect discovery runs to return real upcoming or live events
  instead of mock data.
- Owners/Admins who govern which connectors are runnable and need clear blocked
  or misconfigured states.
- Future implementation agents extending Playwright, Selenium, and incremental
  sync on top of a stable live-source contract.

## Affected Product Docs

- `docs/product/source-registry-and-policy.md`
- `docs/product/discovery-job-lifecycle.md`
- `docs/product/live-feed-and-api-discovery.md`
- `docs/product/platform-and-automation-policy.md`

## Non-Goals

- Public website scraping via Playwright.
- Selenium or alternate browser-adapter discovery.
- Interactive login, headed sessions, or saved browser-state reuse.
- Scheduled polling, background sync, or cursor-based incremental refresh.
- Full connector-health analytics dashboards.
