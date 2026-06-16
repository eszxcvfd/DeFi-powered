# Validation

## Proof Strategy

This story is done only when LiveLead can create user-scoped in-app
notifications, attempt bounded email deliveries, honor notification preference
settings, and keep every notification source and delivery outcome explainable
without leaking provider secrets.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Candidate-generation rules, preference filtering, unread/read/dismiss state transitions, upcoming-event timing eligibility, and delivery suppression rules. |
| Integration | Notification inbox persistence, preference reads/updates, reminder/job/event trigger paths, email-delivery attempt recording, tenant scoping, and unauthorized cross-user access denial. |
| E2E | User sees a new in-app alert, marks it read or dismissed, changes preferences, and confirms future notification behavior reflects the updated settings. |
| Platform | Story verification command proves backend, frontend, and notification adapter fixtures succeed without weakening auth, reminder, or discovery-job proof paths. |
| Performance | Inbox queries remain bounded for normal user volumes, and duplicate notification generation is controlled for repeated job or reminder transitions. |
| Logs/Audit | Preference changes, state transitions, delivery attempts, suppressions, and provider failures create explainable logs/audit evidence without leaking secrets. |

## Fixtures

- At least one user with active membership and email-capable preference state.
- One reminder fixture that becomes due or overdue.
- One discovery job fixture that completes, fails, or needs user action.
- One event fixture with a trustworthy upcoming start time.
- One provider adapter fixture for successful delivery and one for failed or
  suppressed delivery.

## Commands

```bash
./scripts/verify-us-029.sh
```

The script runs:

- `tests/unit/test_notifications_policy.py` (28 unit cases)
- `tests/integration/test_notifications_api.py` (10 integration cases)
- `frontend/e2e/notifications.spec.ts` (1 e2e case)
- `scripts/bin/harness-cli story verify US-029` records the matrix
  result separately.

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports US-029 as `implemented`
  with `unit=yes, integ=yes, e2e=yes, plat=yes`.
- `scripts/bin/harness-cli story verify US-029` returns `pass` and
  stamps `last_verified_at` and `last_verified_result=pass`.
- A representative e2e run covers: sign in as the bootstrap owner,
  open the inbox and preferences pages, change a preference, trigger
  the admin scan from the UI, and confirm the read/dismiss lifecycle
  plus the audit log entries for `notification.preference_changed`
  and `notification.delivered` when a candidate is generated.
- Unit and integration tests cover eligibility, preference filtering,
  default seed matrix, email provider failure redaction, role gating,
  and tenant-scoped inbox queries.
