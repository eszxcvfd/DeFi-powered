# Validation

## Proof Strategy

This story is done only when LiveLead can show a durable engagement plan for a
scored event, group tasks by phase, preserve task state changes, and keep plan
guidance clearly separate from generated content or external execution.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Plan-phase rules, task-state transitions, deterministic task generation, and anti-spam or unsupported-action guardrails. |
| Integration | Plan persistence, task updates, event-detail engagement payloads, and no-plan empty states. |
| E2E | Analyst or sales user opens scored event detail, creates or views an engagement plan, and updates at least one task status. |
| Platform | Story verify command keeps backend engagement planning, API detail behavior, and frontend task-review checks wired into the Harness matrix. |
| Performance | Plan retrieval stays responsive for deterministic local event sets and does not require expensive regeneration on every view. |
| Logs/Audit | Plan creation, refresh, and task-state changes remain diagnosable without implying content approval or external sending. |

## Fixtures

- One scored event with audience hypotheses and enough context to create a
  meaningful plan.
- One event with sparse context that should produce a conservative or partial
  plan.
- Task fixtures spanning before, during, and after event phases.
- Negative fixtures that would tempt spammy or unsupported tasks and must be
  blocked or downgraded.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-008.sh
```

## Acceptance Evidence

- `./scripts/verify-us-008.sh` — ruff (via US-007 chain), pytest unit `test_engagement_generator`, integration `test_engagement_api`.
- Playwright: `frontend/e2e/engagement-plan.spec.ts` (create plan, update task status).
