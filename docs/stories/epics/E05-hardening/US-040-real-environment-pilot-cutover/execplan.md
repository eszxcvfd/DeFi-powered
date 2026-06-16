# Exec Plan

## Goal

Define and implement the first high-risk cutover slice that moves LiveLead from
test-oriented proof into one governed real operator environment with live
connectors, real auth, backup, rollback, and launch controls.

## Scope

In scope:

- Single-host or small-footprint pilot-live environment contract.
- Live-safe runtime configuration split from test defaults.
- Readiness, health, and launch-gate checks.
- Backup, rollback, and pause-live controls.
- Live connector and integration enablement guardrails.
- Operator runbook and post-cutover smoke/UAT proof.

Out of scope:

- Full enterprise production maturity.
- Kubernetes or multi-region deployment.
- Zero-downtime release orchestration.
- Broad performance optimization beyond critical live thresholds.
- Global adaptive operations or cost-optimization programs.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Data model.
- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- Any path that leaves dev headers trusted in live mode.
- Any path that enables live integrations without policy gates or rollback.
- Any weakening of backup, audit, or security requirements for cutover speed.

## Work Phases

1. Discovery: confirm live-environment requirements from `SPEC.md`, runtime
   docs, auth boundary, connector policy, and hardening constraints.
2. Design: define environment profile, launch-gate rules, backup metadata,
   rollback path, and live-toggle ownership.
3. Validation planning: design proof for readiness, auth hardening, connector
   safety, backup freshness, and pilot-live UAT.
4. Implementation: add runtime-readiness surfaces, live-mode config handling,
   operational controls, and the minimum documented runbook/checklist.
5. Verification: prove the environment can enter live mode, run smoke/UAT
   flows, and pause or roll back safely.
6. Harness update: keep product/runtime docs current, update durable story
   status, and leave a clean handoff for later observability or scale stories.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring architecture changes beyond the accepted
  single-host MVP baseline.
- Product direction becomes ambiguous between a pilot-live cutover and a full
  production-platform program.
- Validation would need to skip auth hardening, backup rehearsal, or rollback
  documentation to meet schedule.
- A live connector or AI provider cannot be enabled without violating source
  policy or security guardrails.
