# Overview

## Current Behavior

LiveLead already covers real-source discovery through official feeds/APIs and a
public-website `Playwright` baseline. However, `SPEC.md` still requires one
experimental connector path through `Selenium` or an alternate adapter, and the
project does not yet have a dedicated discovery contract for that engine family.
The browser-session and read-only action contracts are separate surfaces, so the
remaining gap is discovery-specific: a governed alternate-adapter path that can
run bounded extraction recipes without changing business rules.

## Target Behavior

This story should establish the first `Selenium`/alternate-adapter discovery
slice for LiveLead:

- Run approved discovery connectors through a `Selenium` or alternate adapter
  from the existing manual discovery-job workflow.
- Keep engine choice source-scoped and policy-aware behind the shared browser
  adapter boundary.
- Reuse the bounded read-only discovery recipe model for extraction, budgets,
  and safe-stop behavior.
- Turn alternate-adapter extraction output into canonical events and source
  observations that appear in the existing event review surfaces.
- Preserve per-source progress, partial success, and blocked/needs-user-action
  states across mixed-engine discovery runs.

This story should complete the third discovery connector family in the current
acceptance path without widening into login-required browsing, distributed grid
operations UX, or full optional-engine governance.

## Affected Users

- Analysts who need discovery to keep working for approved sources that need a
  `WebDriver`-style adapter instead of `Playwright`.
- Owners/Admins who govern engine choice and need clear blocked or
  misconfigured-state visibility for alternate adapters.
- Future implementation agents extending optional engines, richer connector
  health, or advanced runtime orchestration on top of a stable alternate-adapter
  discovery contract.

## Affected Product Docs

- `docs/product/public-website-playwright-discovery.md`
- `docs/product/selenium-and-alternate-adapter-discovery.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/platform-and-automation-policy.md`

## Non-Goals

- Interactive login or saved browser-state reuse.
- Manual browser-session UX.
- Confirmation-gated actions or external-side-effect actions.
- CloakBrowser policy expansion beyond its separate governance contract.
- Full distributed grid admin UX or connector-health dashboards.
