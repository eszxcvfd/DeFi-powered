# Exec Plan

## Goal

Define and implement the first governed feedback-learning slice so LiveLead can
turn campaign feedback signals into reviewable scoring-weight suggestions without
auto-applying ranking changes.

## Scope

In scope:

- Campaign-scoped scoring-suggestion generation.
- Structured proposed weight deltas with rationale and confidence.
- Approval or rejection workflow for suggestion sets.
- New campaign weight snapshots created only after approval.
- Audit-friendly history for suggestions and decisions.

Out of scope:

- Autonomous optimization of active ranking behavior.
- Cross-tenant or global learning.
- Prompt or provider mutation from feedback alone.
- Broad analytics dashboards.
- Generic AI memory or personalization.

## Risk Classification

Risk flags:

- Audit/security.
- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Any behavior that changes active scoring weights without approval.
- Any weakening of tenant scoping, auditability, or existing scoring history.

## Work Phases

1. Discovery: confirm `FR-SCO-006` plus feedback-signal and campaign-weight
   constraints from `SPEC.md` and current product contracts.
2. Design: define signal sources, suggestion-set structure, approval states, and
   weight-snapshot update rules.
3. Validation planning: design proof for no-auto-apply guardrails, campaign
   scoping, authorization, and audit history.
4. Implementation: add bounded suggestion APIs, persistence, campaign-weight
   snapshot updates, and UI review controls.
5. Verification: prove suggestion generation stays explainable and that active
   weights change only after explicit approval.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for later adaptive-ranking or AI-memory stories.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring cross-campaign or cross-tenant learning.
- Product behavior becomes ambiguous between suggestion review and direct weight
  editing.
- Validation would need to weaken weight-history preservation or approval
  gating.
- The story starts depending on generalized analytics dashboards or autonomous
  experimentation to feel complete.
