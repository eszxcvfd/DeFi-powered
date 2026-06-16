# Design

## Domain Model

The story should formalize the first governed public-website discovery objects:

- `BrowserDiscoveryRecipe`: source-scoped recipe metadata for start URL, wait
  condition, locator strategy, pagination/scroll rules, extraction fields,
  page/time budgets, and snapshot policy.
- `PlaywrightDiscoveryRunResult`: per-job, per-source browser-run outcome with
  counts, visited-page summary, safe-stop state, and provenance summary.
- `WebsiteSourceObservation`: normalized extracted item projection that keeps
  public-website evidence before canonical event merge/deduplication.

Business rules:

- Browser discovery is used only when source policy and connector suitability
  choose it after official feed/API preference is evaluated.
- The first recipe baseline remains read-only and extraction-only; it must not
  depend on login, form submission, or external-side-effect actions.
- Page/time budgets, selector stability rules, and challenge detection are part
  of product behavior, not incidental adapter details.
- Successful website results from one source remain usable even when sibling
  sources in the same job fail or become blocked.
- Challenge or policy block states become denied or `NEEDS_USER_ACTION`, not
  silent bypass attempts.

## Application Flow

- `LaunchDiscoveryJob` continues to orchestrate manual discovery, now selecting
  a `Playwright` browser-discovery runner for eligible website sources.
- `ResolveBrowserDiscoveryRecipe` validates source policy, connector readiness,
  and recipe completeness before any browser worker execution begins.
- `RunPlaywrightDiscoveryRecipe` executes bounded read-only navigation, wait,
  pagination/scroll, detail-open, and extraction steps through the shared
  adapter boundary.
- `NormalizeWebsiteDiscoveryOutput` transforms extracted items into the
  existing canonical event and source-observation pipeline.
- `ProjectBrowserDiscoveryOutcome` enriches job progress/detail with website
  connector counts, blocked reasons, and challenge-safe outcomes.

## Interface Contract

This baseline should extend current discovery and admin surfaces rather than add
new end-user browser APIs:

- `POST /campaigns/{id}/discovery-jobs` should allow approved website
  connectors to run inside the existing selected-source workflow.
- `GET /discovery-jobs/{id}` should expose per-source browser-discovery outcome
  details suitable for progress, partial success, and blocked-state UX.
- `GET /campaigns/{id}/events` and `GET /events/{id}` remain the review
  endpoints for results created from website extraction.
- `GET /admin/connectors` should expose recipe-readiness state and blocked
  reasons without revealing sensitive recipe details.

Expected payload concerns:

- Discovery job responses should distinguish website/browser connectors from
  feed/API connectors during mixed-source runs.
- Browser-discovery errors should stay action-oriented and secret-safe rather
  than dumping low-level traces by default.
- Event review payloads should expose public-website provenance without leaking
  selectors, internal snapshot paths, or hidden adapter metadata.

## Data Model

- Extend connector/source persistence so website connectors can store bounded
  browser recipe metadata and `Playwright`-specific readiness flags.
- Preserve per-source browser-run diagnostics, visited URL context, and safe
  outcome state alongside discovery job progress or source observations.
- Keep canonical event and source-observation storage as the durable review
  truth instead of introducing a separate browser-results silo.
- Add query support needed for website-connector status and mixed-source job
  progress if current structures are not sufficient.

## UI / Platform Impact

- Campaign discovery UI should allow analysts to include approved public website
  connectors in the existing discovery workflow.
- Discovery progress UI should show website connector status coherently beside
  feed/API sources.
- Event review UI should keep one canonical list/detail flow regardless of
  whether results came from feed/API or website extraction.
- Platform work should run through the isolated browser-worker and shared
  adapter boundary, without turning this story into the manual browser-session
  console.

## Observability

- Record structured diagnostics for recipe validation, policy deny, adapter
  start/stop, extraction counts, challenge detection, and safe-stop reasons.
- Keep logs and audit outputs secret-safe while preserving source id, connector
  type, discovery job id, and actor context where applicable.
- Preserve enough metrics or counters to support later connector-health
  reporting without requiring that dashboard in this baseline.

## Alternatives Considered

1. Reuse the manual browser-session console for discovery extraction. Rejected
   because discovery needs automated bounded recipes inside jobs, not a human
   driving a console for every run.
2. Jump directly to Selenium and Playwright together in one slice. Rejected
   because `SPEC.md` calls out a distinct `Playwright` acceptance path and the
   smaller slice is easier to prove safely.
3. Let website discovery write raw scraped rows outside canonical event review.
   Rejected because users only see value when website findings become normal
   event-review data.
