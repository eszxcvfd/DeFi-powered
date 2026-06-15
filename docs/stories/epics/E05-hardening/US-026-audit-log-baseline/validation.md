# Validation

## Proof Strategy

This story is done only when LiveLead can record representative sensitive
actions in a tenant-scoped, secret-safe audit model, expose a read-only admin
audit surface, and block unauthorized or cross-tenant access without weakening
existing product behavior.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Event normalization, redaction rules, append-only write behavior, actor/target mapping, and outcome classification. |
| Integration | Audit persistence, role-gated reads, tenant isolation, representative workflow capture, and blocked unauthorized detail reads. |
| E2E | Owner/Admin opens Settings -> Audit Log, filters entries from an implemented workflow, and views a redacted detail record. |
| Platform | Story verify command keeps audit APIs, representative workflow hooks, and admin audit UI wired into the Harness matrix. |
| Performance | Audit list filtering remains responsive in local proof conditions, and representative workflows do not fail when audit writes occur. |
| Logs/Audit | Login outcome, policy denial, content-review decision, browser confirmation, and lead-state change remain diagnosable with actor, target, result, and correlation context but no secrets. |

## Fixtures

- Seeded multi-tenant workspace with owner/admin actor and non-admin actor.
- Representative implemented workflow fixtures for login outcome, source-policy
  decision, content approval/rejection, confirmation-gated browser action, and
  lead-stage change.
- Cross-tenant read fixture and unauthorized viewer fixture for negative-path
  proof.
- Redaction fixture containing secret-like metadata to prove safe persistence.

## Commands

```text
- ./scripts/verify-us-026.sh — planned story verification chain for audit-governance coverage
- frontend/e2e/audit-log.spec.ts — planned browser proof for admin audit filtering and detail review
```

## Acceptance Evidence

- `tests/unit/test_audit_log_model.py` — normalization, redaction, and append-only write rules
- `tests/integration/test_audit_log_api.py` — list/detail reads, tenant isolation, and representative workflow capture
- Admin UI with audit-log filters and redacted detail visibility
- `scripts/bin/harness-cli story verify US-026` — pass after the verify command is added
