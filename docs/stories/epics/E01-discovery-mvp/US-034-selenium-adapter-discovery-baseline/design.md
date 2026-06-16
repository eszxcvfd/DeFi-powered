# Design

## Domain Model

The story should formalize the first governed alternate-adapter discovery
objects:

- `AlternateBrowserEngineConfig`: source-scoped engine selection metadata that
  records when `Selenium` or another approved adapter is required and why.
- `AlternateAdapterRunResult`: per-job, per-source browser-run outcome with
  engine family, counts, safe-stop state, and provenance summary.
- `AlternateAdapterSourceObservation`: normalized extracted item projection
  that keeps reviewable evidence before canonical event merge/deduplication.

Business rules:

- Alternate-adapter discovery is a governed fallback after official feed/API and
  suitable `Playwright` paths are considered.
- Engine choice stays in connector/policy configuration, not in business logic
  branches tied directly to SDK-specific behavior.
- The first `Selenium` baseline remains read-only and extraction-only; it must
  not depend on login, form submission, or other external-side-effect actions.
- Shared page/time budgets, locator stability expectations, and challenge
  detection remain product rules regardless of which browser adapter runs.
- Successful alternate-adapter results remain usable even when sibling sources
  in the same discovery job fail or are blocked.

## Application Flow

- `LaunchDiscoveryJob` continues orchestrating manual discovery, now selecting a
  `Selenium`/alternate-adapter runner for eligible sources.
- `ResolveAlternateAdapterEligibility` validates source policy, engine
  approval, and recipe completeness before worker execution begins.
- `RunAlternateAdapterDiscoveryRecipe` executes bounded read-only navigation,
  wait, pagination/scroll, detail-open, and extraction steps through the common
  browser interface.
- `NormalizeAlternateAdapterOutput` transforms extracted items into the existing
  canonical event and source-observation pipeline.
- `ProjectAlternateAdapterOutcome` enriches job progress/detail with engine
  family, counts, blocked reasons, and challenge-safe outcomes.

## Interface Contract

This baseline should extend current discovery and admin surfaces rather than add
new end-user browser APIs:

- `POST /campaigns/{id}/discovery-jobs` should allow approved alternate-adapter
  connectors to run inside the existing selected-source workflow.
- `GET /discovery-jobs/{id}` should expose per-source engine family and
  alternate-adapter outcome details suitable for progress and blocked-state UX.
- `GET /campaigns/{id}/events` and `GET /events/{id}` remain the review
  endpoints for results created from alternate-adapter extraction.
- `GET /admin/connectors` should expose engine-readiness state and blocked
  reasons without revealing sensitive driver details.

Expected payload concerns:

- Discovery job responses should distinguish alternate-adapter browser
  connectors from `Playwright` and feed/API connectors during mixed-source runs.
- Alternate-adapter errors should stay action-oriented and secret-safe rather
  than dumping raw driver internals by default.
- Event review payloads should expose engine-aware provenance without leaking
  selector internals, trace paths, or hidden adapter metadata.

## Data Model

- Extend connector/source persistence so sources can store explicit engine
  selection and bounded readiness metadata for `Selenium`/alternate adapters.
- Preserve per-source browser-run diagnostics, engine family, visited URL
  context, and safe outcome state alongside discovery job progress or source
  observations.
- Keep canonical event and source-observation storage as the durable review
  truth instead of creating an engine-specific result silo.
- Add query support needed for engine-specific status and mixed-source progress
  if current structures are not sufficient.

## UI / Platform Impact

- Campaign discovery UI should allow analysts to include approved
  alternate-adapter connectors in the same discovery workflow as other sources.
- Discovery progress UI should show engine family coherently beside source
  status for mixed-engine runs.
- Event review UI should stay unified regardless of whether results came from
  feed/API, `Playwright`, or `Selenium`/alternate extraction.
- Platform work should run through the isolated browser-worker and shared
  adapter boundary, keeping alternate engines replaceable by configuration.

## Observability

- Record structured diagnostics for engine selection, policy deny, adapter
  start/stop, extraction counts, challenge detection, and safe-stop reasons.
- Keep logs and audit outputs secret-safe while preserving source id, engine
  family, connector type, discovery job id, and actor context where applicable.
- Preserve enough metrics or counters to support later connector-health
  reporting without requiring that dashboard in this baseline.

## Alternatives Considered

1. Stop at the `Playwright` baseline and leave `Selenium` undocumented.
   Rejected because `SPEC.md` explicitly requires a third experimental
   connector family through `Selenium` or an alternate adapter.
2. Hard-code `Selenium` selection in discovery business logic. Rejected because
   adapter choice must remain configurable and replaceable.
3. Fold optional-engine governance and CloakBrowser concerns into this story.
   Rejected because those approval and kill-switch rules already belong to a
   separate governance surface.
