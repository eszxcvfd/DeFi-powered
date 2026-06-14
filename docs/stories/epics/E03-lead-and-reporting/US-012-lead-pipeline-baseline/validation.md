# Validation

## Proof Strategy

This story is done only when LiveLead can create leads from qualified event or
manual context, track them in default pipeline stages, expose baseline activity
history, and prevent obvious duplicates without depending on later reminder or
reporting stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Lead-origin validation, source-or-manual-entry rule, duplicate matching, stage-transition guards, and activity-entry creation rules. |
| Integration | `POST /leads`, `GET /leads`, `GET /leads/{id}`, and `PATCH /leads/{id}` behavior; event-link persistence; duplicate conflict handling; and table/Kanban query support. |
| E2E | User creates a lead from an event, opens the lead pipeline, moves the lead to another stage, adds a note, and sees activity history update. |
| Platform | Story verify command keeps backend lead API, lead persistence, and frontend pipeline flows wired into the Harness matrix. |
| Performance | Lead list and Kanban queries remain responsive for realistic seeded lead counts without introducing N+1 behavior in baseline views. |
| Logs/Audit | Lead create, update, note, and stage-change actions remain diagnosable with actor, timestamp, and event/source provenance. |

## Fixtures

- One qualified event fixture with no linked lead yet.
- One existing lead fixture that should trigger a duplicate warning or block.
- One manual-entry fixture with explicit manual-source note.
- Deterministic users for analyst and sales roles when role-sensitive UI proof
  exists.

## Commands

```text
- ./scripts/verify-us-012.sh — chains through `verify-us-011` / `verify-foundation`, then lead unit/integration tests
- `frontend/e2e/lead-pipeline.spec.ts` — included in foundation e2e suite when run via verify-foundation
```

## Acceptance Evidence

- `tests/unit/test_lead_pipeline.py` — origin, duplicate, stage guards
- `tests/integration/test_lead_pipeline_api.py` — CRUD, event link, duplicate 409
- Lead pipeline UI at `/leads`; event create-lead on event detail
