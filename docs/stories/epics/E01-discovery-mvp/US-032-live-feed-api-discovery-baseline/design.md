# Design

## Domain Model

The story should formalize the first governed live-source discovery objects:

- `LiveExternalSourceConfig`: source-level execution metadata for official
  `API`, `RSS`, `Atom`, `sitemap`, or `ICS` connectors, including parser
  family, endpoint/feed URL, auth mode, and stable identity hints.
- `LiveConnectorRunResult`: per-job, per-source outcome with counts, fetch
  timestamp, safe failure state, and provenance summary.
- `LiveSourceObservation`: normalized raw-item projection that keeps the
  required source evidence before canonical event merge/deduplication.

Business rules:

- Live external feed or API access is preferred over browser automation when a
  suitable official source exists.
- Source policy gates still decide whether a connector can run; live execution
  does not bypass approval, quota, or time-window checks.
- Source items must retain enough identity and provenance for downstream
  deduplication and event review.
- Interactive auth, CAPTCHA, MFA, or similar challenges must become denied or
  `NEEDS_USER_ACTION` outcomes rather than implicit browser fallback.
- Successful items from one source remain usable even when sibling sources in
  the same discovery job fail.

## Application Flow

- `LaunchDiscoveryJob` continues to create a manual job from campaign and
  selected source scope, but now may select live feed or API runners when the
  source contract allows it.
- `ResolveRunnableLiveSources` applies enabled/approved/quota/window policy
  checks and chooses the correct live connector adapter without leaking provider
  details into domain logic.
- `FetchLiveSourceItems` executes request, pagination/window rules, and parser
  mapping for one source while capturing safe diagnostics.
- `NormalizeLiveDiscoveryOutput` transforms fetched items into the existing
  canonical event and source-observation pipeline.
- `ProjectLiveSourceOutcome` enriches job-detail progress with live-source
  counts, denial reasons, and needs-user-action status.

## Interface Contract

This baseline should prefer extending existing routes instead of adding a new
parallel public API surface:

- `POST /campaigns/{id}/discovery-jobs` should allow approved live feed or API
  connectors to run under the current selected-source workflow.
- `GET /discovery-jobs/{id}` should expose per-source live outcome details
  suitable for progress, partial success, and blocked-state UX.
- `GET /campaigns/{id}/events` and `GET /events/{id}` should continue to be the
  review endpoints, now backed by canonical events created from live-source
  output.
- `GET /admin/connectors` should expose enough readiness state for feed or API
  connectors without revealing secrets.

Expected payload concerns:

- Discovery job responses should distinguish mock/demo sources from live
  feed/API sources if both can appear during transition periods.
- Source readiness and failure responses should stay secret-safe and
  action-oriented.
- Event review payloads should expose live-source provenance without leaking raw
  auth material or provider-specific hidden fields.

## Data Model

- Extend source or connector persistence so live feed/API connectors can store
  endpoint/parser metadata and stable identity hints.
- Preserve per-source live fetch diagnostics and timestamps at the discovery job
  outcome or source-observation layer.
- Keep canonical event and source-observation storage as the durable review
  truth rather than introducing a separate live-results silo.
- Add indexes or query support needed for per-job source outcomes and event
  review reads if current structures are not sufficient.

## UI / Platform Impact

- Campaign discovery UI should let analysts run approved live feed/API sources
  through the existing discovery workflow.
- Discovery progress UI should show which live sources succeeded, failed, were
  denied, or require user action.
- Event review UI should not need a separate live-data screen; canonical events
  from live sources should appear in the current list/detail surfaces.
- Platform work stays inside the existing Python worker plus HTTP-client path;
  Playwright/Selenium processes remain out of scope for this slice.

## Observability

- Record structured diagnostics for source selection, denied policy, fetch
  outcome, parse failure, and needs-user-action transitions.
- Keep logs and audit fields secret-safe while preserving source id, connector
  type, discovery job id, and actor context where applicable.
- Preserve metrics that can later support connector health reporting without
  requiring the full analytics dashboard in this baseline.

## Alternatives Considered

1. Start with a Playwright connector before official feeds or APIs. Rejected
   because `SPEC.md` explicitly prefers official `API`/`RSS`/`ICS` access and
   the safer path is smaller for the first real-source slice.
2. Keep live external discovery out of scope until all three experimental
   connector types are ready together. Rejected because users need a real-source
   outcome sooner and the contract can be delivered incrementally.
3. Fetch live source items but keep them outside the canonical event review
   pipeline. Rejected because discovery value is only visible when analysts can
   review resulting canonical events through existing product surfaces.
