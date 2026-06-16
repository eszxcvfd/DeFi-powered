# Exec Plan

## Goal

Define and implement the first governed query-expansion slice so LiveLead can
generate, review, approve, and snapshot discovery-query variants for manual and
scheduled runs without widening into autonomous copilot behavior.

## Scope

In scope:

- Campaign-scoped query expansion generation.
- Grouped variant types for synonym, abbreviation, language, and industry
  phrase suggestions.
- Explicit review/edit approval flow for AI-generated expansion.
- Approved-set reuse in manual and scheduled discovery.
- Immutable expansion snapshots linked to discovery execution.

Out of scope:

- Conversational discovery copilot.
- Autonomous re-generation during active jobs.
- Automatic approval with no user review.
- Glossary/translation admin tooling.
- Expansion-effectiveness analytics dashboards.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Removing or weakening validation requirements.

## Work Phases

1. Discovery: confirm query-expansion requirements from `SPEC.md`, campaign
   brief contracts, and scheduled discovery reuse needs.
2. Design: define variant model, approval states, snapshot linkage, and AI
   review boundaries.
3. Validation planning: design proof for grouped suggestions, review/edit
   workflow, approved-set reuse, and snapshot immutability.
4. Implementation: add expansion storage, generation/approval API/UI flows, and
   run/schedule snapshot linkage.
5. Verification: prove approved expansion sets are reused safely and AI
   suggestions never bypass review.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for discovery-copilot Q&A stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The story would require free-form conversational copilot behavior instead of
  a bounded reviewable expansion artifact.
