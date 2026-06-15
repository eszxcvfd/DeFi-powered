# Validation

## Proof Strategy

This story is done only when LiveLead can govern organization membership through
invitation, acceptance, role change, disable/re-enable, and revoke-access
flows, while preserving tenant isolation, last-owner protection, session
invalidation, and secret-safe audit evidence.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Invitation lifecycle, role-governance matrix, last-owner protection, invite-expiry handling, and membership-session invalidation rules. |
| Integration | `GET /admin/members`, invitation create/revoke, invitation accept, role change, disable/re-enable, revoke access, blocked owner/admin edge cases, and post-revoke protected-route denial. |
| E2E | Owner/admin opens the Members page, creates an invite, sees it listed, accepts it through the UI or invite flow, then changes role or disables access and sees the state update safely. |
| Platform | Story verification command proves backend, frontend, and auth-aware membership fixtures succeed without weakening the `US-027` auth boundary. |
| Performance | Repeated invite or membership reads stay bounded for normal organization sizes; revocation or disable actions invalidate access without long inconsistent windows. |
| Logs/Audit | Invitation and membership-governance actions, including blocked attempts, create redacted audit records without leaking raw invite tokens. |

## Fixtures

- At least one organization with two owner-capable users so last-owner
  protection can be tested safely.
- One admin, one analyst, one reviewer, and one viewer candidate account or
  invite target.
- One pending invitation fixture, one accepted member fixture, and one disabled
  or revoked membership fixture.
- One active authenticated session tied to a member who later loses access.

## Commands

```bash
./scripts/verify-us-028.sh
```

The script runs:

- `tests/unit/test_member_management_policy.py` (17 unit cases)
- `tests/integration/test_member_management_api.py` (13 integration cases)
- `frontend/e2e/member-management.spec.ts` (1 e2e case)
- `scripts/bin/harness-cli story verify US-028` is exercised separately by
  the operator and recorded in the matrix.

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports US-028 as `implemented`
  with `unit=yes, integ=yes, e2e=yes, plat=yes`.
- `scripts/bin/harness-cli story verify US-028` returns `pass` and
  stamps `last_verified_at` and `last_verified_result=pass`.
- A representative e2e run covers: sign in as the bootstrap owner,
  invite a teammate, accept the invitation in a fresh browser context,
  observe the new active member, disable / re-enable, change the role,
  revoke access, and confirm every governance action appears in the
  audit log under the `member` family without leaking the invite token.
- Unit and integration tests cover role governance, last-owner
  protection, invite-expiry, session invalidation, and audit redaction
  of invite tokens.
