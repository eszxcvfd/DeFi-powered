# Exec Plan

## Goal

Define and implement the minimum engagement-planning slice that turns event
analysis into an actionable before/during/after checklist with durable task
state and safe planning guardrails.

## Scope

In scope:

- Engagement-plan creation for scored events.
- Before, during, and after event task grouping.
- Task status, assignee, deadline, and notes.
- Event-detail engagement-plan presentation.
- Proof that plan guidance stays operational without pretending content already
  exists.

Out of scope:

- AI content generation and prompt controls.
- Approval workflow and approval history.
- Copy/export or “used” content lifecycle.
- Browser-assisted or automatic execution.
- Lead creation and pipeline updates.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None beyond preserving compliance and anti-spam boundaries while planning.

## Work Phases

1. Discovery: confirm planning, task-state, and anti-spam requirements from
   `SPEC.md`, product docs, and current event-detail behavior.
2. Design: define plan and task persistence plus safe planning boundaries
   without dragging in content generation or lead workflows.
3. Validation planning: design proof for task structure, state changes,
   plan/event linkage, and deferred content behavior.
4. Implementation: add plan storage, plan-generation flow, task updates, and
   minimal event-detail engagement UI.
5. Verification: prove deterministic engagement planning and task updates end
   to end.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for content-studio slices.

## Stop Conditions

Pause for human confirmation if:

- The story starts depending on AI copy generation to feel useful.
- Plan suggestions require unsupported claims or spammy tactics.
- Validation would need to weaken task auditability or compliance guardrails.
- The engagement surface starts depending on browser execution or lead
  workflows to feel complete.
