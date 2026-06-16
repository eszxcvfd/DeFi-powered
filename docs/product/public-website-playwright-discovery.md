# Public Website Playwright Discovery

Source: `SPEC.md` sections 5.3, 5.4, 7.2, 11, 12, 14.1, 14.2, `UC-01`, and
`UC-04`.

## Product Goal

Analysts need LiveLead to discover real event and livestream candidates from
approved public websites when official `API` or feed sources are missing or not
enough. The product contract should define the first governed browser-recipe
discovery path using `Playwright`, how connector recipes are selected and run
inside the discovery workflow, and how the system extracts reviewable event
evidence without turning discovery into an unrestricted browser console.

## MVP Scope

This product slice covers:

- Running approved public-website discovery connectors through a `Playwright`
  adapter when no suitable official `API`, `RSS`, `Atom`, `sitemap`, or `ICS`
  source is available for that source.
- Supporting the first bounded browser recipe contract with start URL, wait
  conditions, stable locator strategy, pagination or scroll rules, extraction
  fields, page/time budgets, and snapshot policy.
- Executing read-only discovery navigation automatically inside the discovery
  job without requiring the user to open a supervised browser session first.
- Preserving per-source browser-run outcomes, extracted observation evidence,
  and safe failure states needed for canonical event review.
- Normalizing extracted website items through the existing canonical event and
  source-observation pipeline.

This product slice does not yet cover:

- `Selenium` or alternate browser-adapter discovery. The first follow-on slice
  is defined in
  `docs/product/selenium-and-alternate-adapter-discovery.md`.
- Interactive login, consented saved-state reuse, or private/member-only sites.
- Browser session console, manual read-only action controls, or confirmation
  flows already defined by the separate browser-operations product contracts.
- Autonomous posting, messaging, form submission, or other external side
  effects.
- Broad website recipe authoring UI beyond the minimum admin configuration
  needed for the first discovery connector baseline.

## Contract Rules

- Browser-based discovery must be a fallback path after official feed/API
  suitability is checked; it is not the default when an official source exists.
- A public-website connector must not run unless the source is enabled,
  approved, within policy window, and explicitly marked runnable for
  `Playwright` discovery.
- The first recipe baseline must stay read-only and extraction-focused: allowed
  behavior may navigate, wait, paginate, scroll, open details, read text, and
  capture permitted snapshots, but it must not submit forms, authenticate, or
  send communication.
- Recipes should prefer semantic or stable locators over brittle selectors,
  with fallback selectors documented and bounded.
- Each connector run must respect configured page/time budgets and stop safely
  on timeout, unexpected interstitials, or extraction failure.
- CAPTCHA, MFA, bot challenges, or login walls must end in denied or
  `NEEDS_USER_ACTION`; the system must not attempt bypass behavior.
- Extracted items must retain enough provenance for event review, including
  source id, final URL or detail URL when available, observation time, and
  connector type.
- Live website discovery is only complete when extracted items become
  reviewable canonical events in the existing event list and detail surfaces.

## API Surface

- `POST /campaigns/{id}/discovery-jobs`: existing manual launch flow should be
  able to execute approved public-website `Playwright` connectors when source
  policy and connector configuration allow it.
- `GET /discovery-jobs/{id}`: job detail should expose per-source browser-run
  outcome, extracted item counts, safe-stop reasons, and `NEEDS_USER_ACTION`
  states.
- `GET /campaigns/{id}/events` and `GET /events/{id}`: existing event review
  surfaces should expose provenance from website-based discovery without
  leaking hidden selectors, secrets, or unsafe internal traces.
- `GET /admin/connectors`: admin registry responses should surface whether a
  public-website connector is runnable for automated discovery and why it is
  blocked when it is not.

## UI Surface

- Analysts can launch a manual discovery run that includes approved
  public-website connectors without switching to the browser-session console.
- Discovery progress shows which website connectors succeeded, failed, were
  blocked by policy, or require user action.
- Event review surfaces show canonical events discovered from website data using
  the same review flow as feed/API results.
- Admin connector views show bounded recipe readiness and blocked-state reasons
  without exposing raw secrets or unsafe recipe internals.

## Validation Implications

- Unit proof should cover recipe validation, locator-strategy rules, page/time
  budget enforcement, and challenge safe-stop behavior.
- Integration proof should cover fixture-site browser discovery through the
  shared `Playwright` adapter, policy enforcement, extraction mapping, and
  canonical event persistence.
- E2E proof should cover launching a discovery run that includes a public
  website connector and reviewing resulting canonical events.
- Logs and audit proof should confirm website connector selection, safe-stop
  causes, and secret-safe diagnostic output remain explainable.
- Platform proof should confirm the `Playwright` adapter opens and closes clean
  in tests and stays wired into the Harness matrix before Selenium or optional
  engine stories widen scope.
