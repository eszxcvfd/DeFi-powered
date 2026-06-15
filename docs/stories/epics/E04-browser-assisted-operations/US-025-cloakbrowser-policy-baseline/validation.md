# Validation

## Proof Strategy

This story is done only when LiveLead can keep CloakBrowser behind explicit
source-scoped approvals, enforce runtime provenance checks and kill-switch
behavior, and expose explainable allowed or blocked states without widening
browser permissions or bypass behavior.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Approval-scope rules, kill-switch precedence, runtime-policy status mapping, and blocked-reason classification. |
| Integration | Approval persistence, revoke behavior, runtime pin or checksum enforcement, source-scoped engine selection, and denied-state handling. |
| E2E | Admin requests or approves CloakBrowser for one source, sees approved or blocked status, then revokes or disables it and sees the state update safely. |
| Platform | Story verify command keeps CloakBrowser governance APIs, runtime-policy checks, and connector admin surfaces wired into the Harness matrix. |
| Performance | Approval and revoke flows remain responsive locally, and kill-switch evaluation does not leave stale approved states in normal proof conditions. |
| Logs/Audit | Request, approval, revoke, runtime-policy failure, kill-switch activation, and attempted use remain diagnosable with actor, source, policy state, and terminal outcome. |

## Fixtures

- Seeded source record that is eligible to request CloakBrowser but starts
  disabled by default.
- Deterministic approval fixture with Owner/Admin and compliance actors.
- Runtime-policy fixtures for pinned-version pass, checksum or signature pass,
  and checksum-failure blocked behavior.
- Revoked, disabled, and kill-switch-active fixtures for negative-path proof.

## Commands

```text
- ./scripts/verify-us-025.sh — planned story verification chain for CloakBrowser governance coverage
- frontend/e2e/cloakbrowser-policy.spec.ts — planned browser proof for admin approval and blocked-state visibility
```

## Acceptance Evidence

- `tests/unit/test_cloakbrowser_policy.py` — approval rules, kill-switch precedence, and runtime-policy mapping
- `tests/integration/test_cloakbrowser_policy_api.py` — approval persistence, engine selection, and revoke handling
- Admin connector UI with CloakBrowser approval and blocked-state feedback
- `scripts/bin/harness-cli story verify US-025` — pass after the verify command is added
