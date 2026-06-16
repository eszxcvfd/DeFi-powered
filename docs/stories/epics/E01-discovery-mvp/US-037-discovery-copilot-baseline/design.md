# Design

## Domain Model

The story should formalize the first governed discovery-copilot objects:

- `DiscoveryCopilotRequest`: campaign-scoped natural-language discovery prompt
  with optional discovery-prep context and actor metadata.
- `DiscoveryCopilotResponse`: structured response artifact with claims,
  evidence, confidence, assumptions, risk flags, proposed query framing, and
  recommended source scope.
- `DiscoveryCopilotRecommendationLink`: durable linkage from one accepted
  copilot response into query expansion, discovery prep, or schedule setup.

Business rules:

- Copilot answers must stay grounded in allowed campaign/discovery context.
- Structured output is mandatory; the first slice does not rely on free-form
  chat text alone.
- Low-confidence or incomplete evidence is surfaced explicitly instead of
  hidden.
- Accepting a recommendation does not immediately run discovery; it prepares a
  reviewable downstream artifact.
- Risk flags remain part of the first-class output, not an optional appendix.

## Application Flow

- `RespondToDiscoveryQuestion` gathers campaign/discovery context, invokes the
  provider boundary, validates structured output, and returns a bounded copilot
  response.
- `ValidateCopilotSchema` enforces required fields such as claims, evidence,
  confidence, assumptions, and risk flags.
- `ProjectCopilotIntoQueryExpansion` optionally maps recommended search phrasing
  into the governed query-expansion layer instead of bypassing it.
- `LinkCopilotRecommendationToRunPrep` records when a user accepts structured
  guidance for later manual or scheduled discovery setup.
- `ListRecentDiscoveryCopilotResponses` may provide bounded history if needed by
  the first UX, while staying campaign-scoped and reviewable.

## Interface Contract

This baseline should introduce a bounded copilot-planning API, not a generic
chat endpoint:

- `POST /campaigns/{id}/discovery-copilot:respond` accepts a discovery question
  and returns structured output.
- Optional campaign-scoped recent-response route may be added if the first UI
  needs bounded history.
- Query-expansion and discovery-prep routes remain the owners of approved
  execution artifacts.

Expected payload concerns:

- Responses should include structured sections for claims, evidence,
  confidence, assumptions, risk flags, proposed query framing, and recommended
  sources.
- Validation should reject malformed or under-specified provider payloads rather
  than silently downgrading into opaque prose.
- Accepted recommendations should link to downstream artifacts without creating
  a hidden execution path.

## Data Model

- Add durable storage only if needed for recent copilot responses, acceptance
  history, or audit/provenance requirements.
- Preserve structured response payloads and downstream linkage in a secret-safe,
  tenant-scoped way.
- Reuse existing campaign/discovery ownership boundaries instead of creating a
  repo-wide AI conversation log.
- Add lookup support needed for bounded recent-response views and acceptance
  linkage if current structures are not sufficient.

## UI / Platform Impact

- Campaign/discovery prep UI should offer a bounded copilot panel or sidecar
  for discovery questions.
- Structured response UI should highlight claims/evidence/confidence and show
  assumptions/risk flags prominently.
- Users should be able to move recommended query framing into governed query
  expansion or prep flows with explicit control.
- Platform work stays inside the existing AI/provider boundary plus campaign/
  discovery surfaces; this is not yet a generic assistant shell.

## Observability

- Record structured diagnostics for request grounding, provider response
  validation, confidence/risk output, and accepted recommendation linkage.
- Keep audit outputs explainable with actor, campaign id, request id, response
  id, and downstream artifact linkage where applicable.
- Preserve enough counters/metrics to support later feedback/quality work
  without requiring that dashboard in this baseline.

## Alternatives Considered

1. Treat discovery copilot as plain chat with no schema. Rejected because
   `SPEC.md` and AI output rules require structured, reviewable outputs.
2. Let copilot run discovery directly after answering. Rejected because the
   product remains human-controlled and review-first.
3. Skip the copilot layer and only keep query expansion. Rejected because
   `SPEC.md` explicitly calls for a natural-language Q&A mode.
