# Exec Plan

## Goal

Define and implement the minimum audience-analysis slice that turns ranked
events into interpretable opportunities through explainable audience
hypotheses, evidence links, and privacy-safe inference boundaries.

## Scope

In scope:

- Audience hypothesis generation for canonical scored events.
- Evidence linking and inference labeling.
- Confidence-aware audience persistence and event-detail presentation.
- Safe empty or pending states when context is insufficient.
- Proof that audience analysis is explainable and respects sensitive-inference
  boundaries.

Out of scope:

- User feedback loops on hypothesis accuracy.
- Engagement-plan or content-generation workflows.
- Private attendee enrichment or identity resolution.
- Bulk compare, bulk outreach, or lead conversion behavior.
- Browser-assisted audience actions.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Audit/security because the story touches inference boundaries and sensitive
  attribute restrictions.

## Work Phases

1. Discovery: confirm audience, evidence, and privacy requirements from
   `SPEC.md`, product docs, and current score/event-detail behavior.
2. Design: define audience-hypothesis persistence, evidence payloads, and safe
   inference boundaries without dragging in engagement or lead workflows.
3. Validation planning: design proof for hypothesis quality, evidence labeling,
   sensitive-inference blocking, and event-detail visibility.
4. Implementation: add audience storage, generation flow, event-detail
   contract, and minimal audience UI.
5. Verification: prove deterministic or labeled audience analysis end to end.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for feedback and engagement slices.

## Stop Conditions

Pause for human confirmation if:

- Audience generation requires private attendee data or unsupported enrichment.
- Product value depends on inferring sensitive attributes or identity claims.
- Validation would need to weaken explainability or privacy guarantees.
- The audience surface starts depending on engagement, feedback, or lead
  workflows to feel complete.
