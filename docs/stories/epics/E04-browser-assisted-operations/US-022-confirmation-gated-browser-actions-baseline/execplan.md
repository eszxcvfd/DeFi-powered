# Exec Plan

## Goal

Define and implement the first preview and confirmation slice for destructive or
external-side-effect browser actions so supervised users can review, confirm, or
cancel those actions safely before execution.

## Scope

In scope:

- Classification of side-effect browser actions that require confirmation.
- Preview or dry-run output before execution.
- Explicit confirm and cancel transitions for one requested action.
- Confirmation-required and post-decision session state visibility.
- Audit context for request, confirm, cancel, and execution outcomes.

Out of scope:

- Screenshot, console-log, or trace retention.
- Browser profile lifecycle workflows.
- CloakBrowser approval workflow.
- Bulk autonomous communication or standing approvals.
- Broad workflow orchestration beyond one confirmation-gated action at a time.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Audit/security.
- Cross-platform.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- External-side-effect browser behavior and audit expectations keep this story
  high-risk.

## Work Phases

1. Discovery: confirm side-effect action, preview, and confirmation expectations
   from `SPEC.md`, action policy, and existing browser stories.
2. Design: define confirmation scoping, preview semantics, confirm/cancel
   transitions, and audit context.
3. Validation planning: design proof for classification, preview consistency,
   confirm/cancel behavior, and blocked or expired paths.
4. Implementation: extend browser-action flow with preview and confirmation-
   gated execution plus session UI state.
5. Verification: prove users can request, review, confirm, or cancel a
   side-effect action safely.
6. Harness update: leave a clean handoff for artifact-retention, profile, and
   CloakBrowser policy stories.

## Stop Conditions

Pause for human confirmation if:

- The story needs blanket approval across multiple actions or sessions.
- Preview output cannot stay meaningfully aligned with the executable action.
- Validation requirements need to weaken around audit visibility or
  confirmation scoping.
- The implementation needs to bypass the current browser-session and
  browser-action governance model.
