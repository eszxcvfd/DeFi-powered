# Validation

## Proof Strategy

This story is done only when LiveLead can turn lead follow-up dates into due or
overdue reminders, show those reminders in the product, let users complete or
reschedule them, and provide baseline in-app reminder visibility without
depending on later email or reporting stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Reminder scheduling rules, due versus overdue classification, reminder-state transitions, completion or reschedule guards, and audit-entry creation. |
| Integration | Reminder queue query behavior, lead-linked reminder persistence, reminder completion and reschedule APIs, and reminder summaries in lead payloads. |
| E2E | User sets or updates a lead follow-up date, sees a due reminder in the queue or lead surface, completes or reschedules it, and sees status feedback update. |
| Platform | Story verify command keeps backend reminder behavior, lead reminder summaries, and frontend reminder workflows wired into the Harness matrix. |
| Performance | Reminder queue queries remain responsive for realistic seeded reminder counts without hidden N+1 behavior in lead-linked views. |
| Logs/Audit | Reminder creation, due classification, completion, and reschedule actions remain diagnosable with actor, timestamp, lead id, and original due time context. |

## Fixtures

- One lead fixture with a future follow-up date.
- One lead fixture with a due reminder ready to surface in the queue.
- One lead fixture with an overdue reminder.
- Deterministic users for reminder owner and reviewer or admin visibility when
  role-sensitive UI proof exists.

## Commands

```text
- ./scripts/verify-us-013.sh — chains through `verify-us-012` / foundation, then reminder unit/integration tests
- `frontend/e2e/follow-up-reminders.spec.ts` — included in foundation e2e when run via verify-foundation
```

## Acceptance Evidence

- `tests/unit/test_follow_up_reminders.py` — due/overdue classification and state guards
- `tests/integration/test_follow_up_reminders_api.py` — queue, alerts, complete, reschedule, lead reminder summary
- Reminder queue and in-app banner on `/leads` and app shell
- `./scripts/verify-foundation.sh` — 13 Playwright e2e passed (incl. `follow-up-reminders`, `lead-pipeline`)
- `scripts/bin/harness-cli story verify US-013` — pass (full platform chain)
