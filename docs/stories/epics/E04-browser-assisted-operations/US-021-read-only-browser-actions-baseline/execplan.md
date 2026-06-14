# Exec Plan

## Goal

Define and implement the first allowlisted read-only browser-action slice that
lets users execute safe supervised actions inside an active browser session with
clear lifecycle feedback, selector guardrails, and timeout or budget protection.

## Scope

In scope:

- Connector-allowlisted read-only browser actions for active sessions.
- A bounded first action set such as navigate, scroll, open detail, and read
  text.
- Action lifecycle updates for the browser session UI.
- Selector resilience rules and timeout or budget enforcement.
- Safe blocked or needs-user-action behavior for unsupported or challenge states.

Out of scope:

- Destructive or external-side-effect action confirmation.
- Dry-run preview for submit actions.
- Screenshot, console-log, or trace retention.
- Browser profile lifecycle workflows.
- CloakBrowser approval or outbound communication automation.

## Risk Classification

Risk flags:

- External systems.
- Public contracts.
- Cross-platform.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- External provider behavior through browser automation keeps this story
  high-risk even though the first action set stays read-only.

## Work Phases

1. Discovery: confirm allowlisted-action requirements from `SPEC.md`, action
   classification policy, and the browser-session baseline.
2. Design: define supported read-only actions, selector strategy, and timeout or
   budget behavior.
3. Validation planning: design proof for allowlist enforcement, action events,
   challenge handling, and safe failure paths.
4. Implementation: add action execution through the shared browser interface and
   expose controls in the session UI.
5. Verification: prove users can run supported read-only actions and understand
   the resulting status updates.
6. Harness update: leave a clean handoff for confirmation, dry-run, and
   artifact stories.

## Stop Conditions

Pause for human confirmation if:

- The story needs submit, post, or account-changing actions to be valuable.
- Connector policy cannot express a stable allowlist boundary for read-only
  actions.
- Validation requirements need to weaken around selector resilience, budget
  enforcement, or challenge handling.
- The implementation needs to bypass the current shared browser-adapter boundary.
