# Exec Plan

## Goal

Define and implement the minimum approved-content handoff slice that lets users
copy or export approved content, mark it used, and preserve audit visibility
without automating outbound actions.

## Scope

In scope:

- Approved-only copy/export flow.
- Approved-to-used lifecycle transition.
- Handoff audit metadata.
- Usage-status visibility in content-studio views.
- Proof that handoff remains human-controlled and separate from sending.

Out of scope:

- Browser-assisted or automatic sending.
- `ARCHIVED` lifecycle transitions.
- Usage analytics.
- Lead or pipeline actions.
- Bulk publishing workflows.

## Risk Classification

Risk flags:

- Audit/security.
- Public contracts.
- Cross-platform.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None beyond preserving approved-only gating and audit history expectations.

## Work Phases

1. Discovery: confirm export, handoff, and used-state requirements from
   `SPEC.md`, product docs, and current approval behavior.
2. Design: define handoff records, export contract, and used-state boundaries
   without dragging in send or archive workflows.
3. Validation planning: design proof for approved-only gating, export output,
   and used-state history.
4. Implementation: add handoff persistence, export flow, usage-state updates,
   and UI feedback.
5. Verification: prove copy/export and mark-used behavior end to end.
6. Harness update: record story proof, keep product docs current, and leave a
   clean handoff for send or archive stories.

## Stop Conditions

Pause for human confirmation if:

- Export requirements force a broader file-format or compliance decision.
- Validation would need to weaken auditability or approved-only gating.
- The story starts depending on send automation or archive behavior to feel
  complete.
- Used-state semantics conflict with an unstated business rule about what
  counts as real-world usage.
