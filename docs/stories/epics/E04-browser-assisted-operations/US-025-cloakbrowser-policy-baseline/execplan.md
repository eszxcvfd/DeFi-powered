# Exec Plan

## Goal

Define the first CloakBrowser policy slice so LiveLead can keep the optional
engine behind explicit source-scoped approvals, runtime provenance controls,
and kill-switch behavior rather than treating it like a default browser mode.

## Scope

In scope:

- Owner/Admin and compliance approval requirements for source-scoped
  CloakBrowser enablement.
- Approval metadata, revoke behavior, and kill-switch controls.
- Runtime policy for version pinning, checksum or signature verification when
  available, and no silent production auto-upgrades.
- Connector and session blocked-state behavior when CloakBrowser is unapproved,
  revoked, disabled, or fails runtime-policy checks.
- Admin visibility into CloakBrowser approval and policy status.

Out of scope:

- Any permission to bypass CAPTCHA, MFA, login challenges, or source terms.
- Making CloakBrowser the default browser engine.
- Broad compliance workflow automation outside this bounded approval slice.
- New browser action permissions beyond existing session, action, confirmation,
  artifact, and profile stories.
- Packaging or deployment redesign beyond the bounded runtime-policy contract.

## Risk Classification

Risk flags:

- Authorization.
- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- External provider behavior and audit/security because CloakBrowser enablement
  changes which browser runtime may touch a third-party source and how that
  decision is governed.

## Work Phases

1. Discovery: confirm approval, provenance, kill-switch, and blocked-state
   requirements from `SPEC.md`, source policy, and platform policy.
2. Design: define approval scope, runtime-policy checks, and revoke semantics.
3. Validation planning: design proof for allowed, denied, revoked, and runtime-
   policy-failed CloakBrowser states.
4. Implementation: add the bounded policy, approval, and admin-governance
   surfaces.
5. Verification: prove CloakBrowser can be allowed only when all approvals and
   runtime checks pass, and disabled quickly when they do not.
6. Harness update: leave a clean handoff for later hardening or packaging work.

## Stop Conditions

Pause for human confirmation if:

- The story requires behavior that could be read as bypassing source terms or
  anti-bot challenges.
- Approval scope needs to cross tenant boundaries or weaken role gates.
- Runtime policy requires a deployment or packaging architecture change beyond
  the bounded current baseline.
- Validation would need to weaken provenance, checksum, or kill-switch proof.
