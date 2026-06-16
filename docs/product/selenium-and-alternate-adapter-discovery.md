# Selenium And Alternate Adapter Discovery

Source: `SPEC.md` sections 5.3, 5.4, 7.2, 11, 12, 14.1, 14.2, `UC-01`, and
`UC-04`.

## Product Goal

Analysts and admins need a governed fallback discovery path for sources that
cannot be handled reliably by official feeds/APIs or the first `Playwright`
browser recipe baseline. The product contract should define when LiveLead may
run a `Selenium` or alternate adapter connector, how engine selection remains a
configurable adapter concern instead of business logic, and how discovery stays
read-only, reviewable, and safe across differing browser runtimes.

## MVP Scope

This product slice covers:

- Running approved discovery connectors through a `Selenium` or alternate
  adapter path when connector configuration explicitly requires `WebDriver`-
  style behavior or a non-`Playwright` compatibility route.
- Supporting source-scoped engine selection through the shared discovery
  connector contract without changing domain/application behavior.
- Executing the same bounded read-only discovery recipe shape used for browser
  extraction: start URL, wait rules, locators, pagination/scroll, extraction
  fields, budgets, and snapshot policy.
- Preserving per-source adapter-engine outcome, extracted observation evidence,
  and safe failure states needed for canonical event review.
- Normalizing extracted items through the existing canonical event and
  source-observation pipeline.

This product slice does not yet cover:

- Interactive login, consented saved-state reuse, or private/member-only sites.
- Manual browser-session console workflows or confirmation-gated browser
  actions.
- Optional CloakBrowser enablement beyond the separate policy/governance
  contract already defined for that engine.
- Automatic engine switching driven by opaque heuristics without explicit source
  policy/configuration.
- Broad connector-health analytics dashboards or distributed grid operations UX.

## Contract Rules

- `Selenium` or alternate adapter discovery must remain a governed fallback,
  not the default when official feed/API or approved `Playwright` discovery is
  suitable.
- A source may run through `Selenium` or another approved alternate adapter
  only when source configuration, policy, and engine approval explicitly allow
  it.
- Engine selection must stay behind a shared adapter boundary; business logic
  cannot branch on provider SDK calls directly.
- The first `Selenium` baseline remains read-only and extraction-focused:
  allowed behavior may navigate, wait, paginate, scroll, open details, read
  text, and capture permitted snapshots, but it must not authenticate, submit,
  or send communication.
- Connector runs must respect configured page/time budgets and stop safely on
  timeout, driver/session failure, unstable DOM, or extraction failure.
- CAPTCHA, MFA, bot challenges, or login walls must end in denied or
  `NEEDS_USER_ACTION`; the system must not attempt bypass behavior.
- Extracted items must retain enough provenance for event review, including
  source id, final/detail URL when available, observation time, connector type,
  and engine family.
- Discovery remains complete only when extracted results become reviewable
  canonical events through the existing event list and detail surfaces.

## API Surface

- `POST /campaigns/{id}/discovery-jobs`: existing manual launch flow should be
  able to execute approved `Selenium` or alternate-adapter connectors when
  policy and connector engine configuration allow it.
- `GET /discovery-jobs/{id}`: job detail should expose per-source engine family,
  browser-run outcome, extracted item counts, safe-stop reasons, and
  `NEEDS_USER_ACTION` states.
- `GET /campaigns/{id}/events` and `GET /events/{id}`: existing event review
  surfaces should expose provenance from alternate-adapter discovery without
  leaking driver internals, selectors, or secrets.
- `GET /admin/connectors`: admin registry responses should surface whether a
  source is runnable through `Selenium`/alternate adapter and why it is blocked
  when it is not.

## UI Surface

- Analysts can launch a manual discovery run that includes approved
  `Selenium`/alternate-adapter connectors through the same discovery workflow as
  other sources.
- Discovery progress shows which sources are running through alternate browser
  engines and whether those sources succeeded, failed, or require user action.
- Event review surfaces show canonical events discovered through alternate
  adapters using the same review flow as feed/API and `Playwright` results.
- Admin connector views show bounded engine readiness and blocked-state reasons
  without exposing unsafe driver or secret details.

## Validation Implications

- Unit proof should cover engine-selection rules, adapter eligibility, shared
  recipe validation, and challenge-safe state mapping.
- Integration proof should cover fixture-site discovery through the shared
  `Selenium`/alternate adapter boundary, policy enforcement, extraction
  mapping, and canonical event persistence.
- E2E proof should cover launching a discovery run that includes an approved
  alternate-adapter connector and reviewing resulting canonical events.
- Logs and audit proof should confirm engine selection, safe-stop causes, and
  secret-safe diagnostic output remain explainable.
- Platform proof should confirm the `Selenium` adapter can complete a read-only
  sample flow through the common interface and stays wired into the Harness
  matrix before broader engine/runtime stories widen scope.
