# Validation

## Proof Strategy

This story is done only when LiveLead can create bounded recurring discovery
schedules, dispatch them through the shared discovery job pipeline, and keep
future runs safe with overlap protection, execution-time policy checks, and
clear operator visibility.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Recurrence validation, next-run calculation, timezone handling, overlap policy, and schedule state transitions. |
| Integration | Schedule persistence, scheduler tick/dispatch, execution-time policy re-check, overlap skip behavior, and discovery-job creation from schedule dispatch. |
| E2E | User creates a schedule, sees next-run preview, observes a scheduled run appear as a normal discovery job, and pauses/resumes the schedule successfully. |
| Platform | Story verification command proves scheduler process dispatches eligible schedules and links them to standard discovery jobs without bypassing the shared orchestration path. |
| Performance | Scheduler scanning and dispatch stay bounded for normal schedule counts and do not create overlapping duplicate runs for the same schedule. |
| Logs/Audit | Schedule create/update/pause/resume, skipped overlap, blocked dispatch, and created-job linkage remain explainable with actor, schedule, campaign, and job context. |

## Fixtures

- At least one campaign with approved discovery sources and a valid schedule.
- One paused or disabled schedule to prove state transitions.
- One schedule configured to collide with an in-progress run to prove overlap
  handling.
- One schedule whose selected source becomes policy-blocked before dispatch to
  prove execution-time re-check behavior.

## Commands

```text
./scripts/verify-us-035.sh
./scripts/bin/harness-cli story verify US-035
```

Proof includes:

- `tests/unit/test_discovery_schedule_recurrence.py`
- `tests/integration/test_discovery_schedules.py`
- `frontend/e2e/discovery-schedule.spec.ts` (when frontend deps are installed)
- `python -m apps.scheduler.main` (scheduler once tick)

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-035` once implemented with
  the expected proof columns populated.
- A representative integration or e2e run shows a scheduled trigger creating a
  standard discovery job.
- Proof shows paused schedules do not dispatch and overlapping schedules follow
  the configured safe behavior.
