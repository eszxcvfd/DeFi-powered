# Exec Plan

## Goal

Define and implement the minimum approval-workflow slice that turns generated
drafts into governed review artifacts with explicit approve or reject actions
and durable audit history.

## Scope

In scope:

- Review-state lifecycle for drafts.
- Approve and reject actions.
- Reviewer notes and decision history.
- Status visibility in content-studio views.
- Proof that only approved drafts are treated as ready for later use.

Out of scope:

- Copy/export actions.
- `USED` and `ARCHIVED` transitions.
- Automatic or browser-assisted sending.
- Reviewer analytics.
- Lead or pipeline actions.

## Risk Classification

Risk flags:

- Authorization.
- Audit/security.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Authorization because review actions may be role-restricted.
- Audit/security because approval history is part of the governance contract.

## Work Phases

1. Discovery: confirm approval states, reviewer semantics, and governance
   requirements from `SPEC.md`, product docs, and current generated-draft
   behavior.
2. Design: define review status, decision history, authorization boundaries,
   and future lifecycle compatibility without dragging in export or sending.
3. Validation planning: design proof for transitions, audit history, and
   unauthorized or invalid review attempts.
4. Implementation: add review persistence, approve/reject actions, and review
   UI status.
5. Verification: prove end-to-end review flow for approve and reject paths.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for export or used-lifecycle stories.

## Stop Conditions

Pause for human confirmation if:

- Approval semantics require a new role or permission model not yet defined.
- Validation would need to weaken reviewer auditability or state rules.
- The story starts depending on export or sending actions to feel complete.
- Review decisions become ambiguous across draft revisions in a way that needs a
  durable decision record.
