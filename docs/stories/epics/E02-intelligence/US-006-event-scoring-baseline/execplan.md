# Exec Plan

## Goal

Define and implement the minimum scoring slice that turns canonical event
review into prioritized work through campaign-aware scoring, explainable
breakdown, and explicit re-score behavior.

## Scope

In scope:

- Campaign-aware score calculation for canonical events.
- Priority threshold mapping and version metadata.
- Score persistence and audit-friendly score history behavior.
- Event list and detail score surfaces.
- Explicit re-score workflow.
- Proof that event ranking is explainable and stable enough for downstream
  audience, engagement, and lead stories.

Out of scope:

- Full audience hypothesis generation.
- Engagement-plan or content-generation workflows.
- Bulk re-score and compare views.
- Lead conversion, reminders, or watchlist automation.
- Browser-assisted event actions.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None beyond preserving current scoring-weight and review-surface contracts.

## Work Phases

1. Discovery: confirm score formula, threshold behavior, and UI scope from
   `SPEC.md`, product docs, and existing event-review behavior.
2. Design: define campaign-aware score storage, explanation payloads, and
   re-score boundaries without dragging in engagement or leads early.
3. Validation planning: design proof for score math, version metadata, ranking
   behavior, and score-detail UI visibility.
4. Implementation: add scoring persistence, calculation flow, list/detail
   contracts, and minimal score UI.
5. Verification: prove deterministic scoring and explicit re-score behavior end
   to end.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for audience and engagement slices.

## Stop Conditions

Pause for human confirmation if:

- The story starts forcing an irreversible cross-campaign score-sharing model.
- Score inputs require unsupported audience inference or sensitive attributes.
- Validation would need to hide missing data or weaken explainability claims.
- The score surface starts depending on engagement, lead, or browser workflows
  to feel complete.
