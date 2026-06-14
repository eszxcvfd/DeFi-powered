# Exec Plan

## Goal

Define and implement the minimum event-results slice that makes discovery
output reviewable through canonical event records, provenance-aware
deduplication, and a stable list/detail workflow.

## Scope

In scope:

- Canonical event persistence for deterministic discovery results.
- Provenance and confidence metadata needed for review.
- Deduplication rules for overlapping source findings.
- Campaign or discovery-linked event list behavior.
- Minimal event detail with overview and source evidence.
- Proof that discovery output survives beyond job status updates.

Out of scope:

- Event scoring and priority explanations.
- Audience hypothesis generation.
- Watchlist, reminders, and bulk re-score.
- Browser-assisted session launch.
- Lead conversion, exports, and CRM sync.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None beyond maintaining current validation requirements.

## Work Phases

1. Discovery: confirm event-result requirements, required source fields, and
   UI-003/UI-004 scope from `SPEC.md` and current product docs.
2. Design: define canonical event, source observation, and deduplication
   boundaries without pulling in scoring or lead concerns early.
3. Validation planning: design proof for merge behavior, provenance exposure,
   and minimal review UI/API flows.
4. Implementation: add persistence, normalization path, event list/detail
   contracts, and minimal frontend review surfaces.
5. Verification: prove deterministic event review end to end, including merge
   cases and evidence visibility.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for later scoring/watchlist work.

## Stop Conditions

Pause for human confirmation if:

- The story starts forcing a cross-campaign canonicalization decision that
  materially changes data ownership assumptions.
- Deduplication requires opaque heuristics that cannot be explained in UI or
  logs.
- Validation would need to weaken provenance, confidence, or source-evidence
  requirements.
- The minimal event review slice starts depending on scoring, lead, or browser
  workflows to feel complete.
