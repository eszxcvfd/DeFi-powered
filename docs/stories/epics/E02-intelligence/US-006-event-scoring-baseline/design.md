# Design

## Domain Model

The story should formalize the first campaign-aware scoring objects:

- `EventScore`: latest or append-only score record linked to an event and
  campaign.
- `EventScoreComponent`: structured component breakdown or equivalent payload
  for weighted factors, raw component values, and missing-data notes.
- `ScoreThresholdProfile` or equivalent configuration snapshot derived from
  workspace rules at calculation time.
- `ScoreRecalculationRequest` or equivalent command boundary for explicit
  re-score behavior.

Business rules:

- Total score must remain within `[0,100]`.
- Priority level must derive from threshold configuration, not ad hoc UI logic.
- Score results must stay campaign-scoped because campaign weights can differ.
- A score explanation must identify evidence-backed components, derived
  heuristics, missing data, and factors that lower confidence or priority.
- Audience-related scoring inputs may use deterministic event cues in this
  story, but they must not claim person-level sensitive inference or pretend a
  full audience hypothesis exists already.
- Re-score must preserve enough metadata to explain what changed between score
  versions.

## Application Flow

Commands:

- Calculate initial score for canonical events after normalization or on
  explicit request.
- Re-score an event when campaign weights or canonical event data change.
- Persist score version metadata and audit-friendly explanation fields.

Queries:

- List campaign events with score summary and priority.
- Get event detail with current score breakdown and score metadata.
- Detect stale or missing scores so the UI can surface a re-score path.

Scoring rules should live in domain or application layers rather than in route
handlers or frontend code. Event review should remain the source of canonical
event truth, while scoring consumes that truth without owning provenance or
deduplication logic.

## Interface Contract

The minimum contract should cover:

- `GET /campaigns/{id}/events` with score summary and priority state.
- `GET /events/{id}` with score breakdown, score version metadata, and
  missing-data explanations.
- `POST /events/{id}/rescore` for an explicit recalculation path.
- Stable response fields for `total_score`, `priority_level`,
  `scoring_version`, `calculated_at`, and a structured component breakdown.

Errors should distinguish missing campaign scope, missing event, invalid
re-score request, and unavailable scoring prerequisites without exposing
storage internals.

## Data Model

Expected persistence work:

- Add campaign-aware score storage linked to canonical events.
- Store total score, priority level, component payloads, explanation payloads,
  scoring version, thresholds or weights snapshot, and calculation timestamp.
- Keep score history append-only or otherwise audit-friendly if updates replace
  the latest surfaced score.
- Avoid pulling engagement, lead, or browser-session tables into this story.

## UI / Platform Impact

- Extend event results with score badge and priority summary.
- Extend event detail with a score surface or score tab aligned with `UI-004`.
- Surface stale-score or missing-score states clearly.
- Keep audience, engagement, and lead actions visibly deferred when they are
  not implemented yet.

## Observability

- Record score calculations and re-score actions in structured logs or
  audit-friendly traces.
- Keep score-version changes explainable for later review.
- Ensure score explanations do not leak secrets, raw credentials, or hidden
  connector internals.

## Alternatives Considered

1. Delay scoring until audience and engagement stories are ready. Rejected
   because users need prioritization immediately after event review, and later
   workflows depend on a stable score surface.
2. Compute scores only in the UI from event payloads. Rejected because it would
   make audit, re-score, and API behavior inconsistent across clients.
