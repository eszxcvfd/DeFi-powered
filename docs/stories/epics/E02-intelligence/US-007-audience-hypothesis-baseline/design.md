# Design

## Domain Model

The story should formalize the first audience-analysis objects:

- `AudienceHypothesis`: audience segment record linked to a canonical event.
- `AudienceEvidenceItem`: structured evidence reference or equivalent payload
  that points to source-backed event cues used by a hypothesis.
- `AudienceInferenceMarker`: metadata that distinguishes observed evidence from
  heuristic or model-assisted inference.
- `AudienceGenerationRun` or equivalent metadata capturing when hypotheses were
  produced and by which strategy version.

Business rules:

- Hypotheses should describe segments such as buyer groups, partner personas,
  or referral cohorts rather than inventing unsupported attendee identities.
- Every hypothesis must include a reason, confidence, and at least one evidence
  reference or explicit inference label.
- Sensitive attributes and protected-category speculation are forbidden output.
- Hypothesis generation must preserve enough metadata to explain the result
  later, including generation strategy or model version when applicable.
- Audience analysis may reuse scored event context, but it must not silently
  mutate canonical event facts or score history.

## Application Flow

Commands:

- Generate or refresh audience hypotheses for a canonical event.
- Persist hypotheses, evidence links, inference labels, and generation
  metadata.
- Mark unsupported or insufficient-context events with a safe empty-state
  result instead of fabricating audience claims.

Queries:

- Get event detail with audience hypotheses and evidence summaries.
- Detect whether an event has pending, missing, or stale audience analysis.

Audience generation should live behind domain or application boundaries so the
first implementation can start deterministic and later adopt model-assisted
strategies without rewriting the UI contract. Evidence linking should consume
canonical event data and source observations without leaking raw secrets or
connector internals.

## Interface Contract

The minimum contract should cover:

- `GET /events/{id}` with audience hypotheses, reasons, confidence, evidence
  summaries, and generation metadata.
- Stable payload fields for `segment_name`, `fit_type`, `reason`,
  `confidence`, `evidence`, and `generated_by` or equivalent strategy markers.
- Clear empty, pending, or unavailable states when event context is
  insufficient for a reliable hypothesis.

Errors should distinguish missing event scope, unavailable analysis state, and
invalid audience payload generation without exposing storage internals or model
implementation details.

## Data Model

Expected persistence work:

- Add audience-hypothesis storage linked to canonical events.
- Store segment name, fit type, reason, confidence, evidence payload,
  generation strategy, and timestamps.
- Preserve whether evidence is directly observed or inferred.
- Avoid pulling engagement-plan, reviewer, or lead-pipeline tables into this
  story.

## UI / Platform Impact

- Extend event detail with an audience section or tab aligned with `UI-004`.
- Show segment, confidence, and evidence context in a reviewable layout.
- Surface safe empty states for events that do not have enough context.
- Keep user feedback, engagement actions, and lead actions visibly deferred.

## Observability

- Record audience-generation runs and safe-block reasons in structured logs or
  audit-friendly traces.
- Keep hypothesis explanations diagnosable when users question why a segment was
  suggested.
- Ensure logs and payloads never expose sensitive-attribute guesses or secret
  source data.

## Alternatives Considered

1. Fold audience analysis into score explanations only. Rejected because users
   need a dedicated audience artifact with evidence, not just a hidden scoring
   component.
2. Delay audience until engagement-plan generation. Rejected because `UC-02`
   expects users to review audience context before deciding what to do next.
