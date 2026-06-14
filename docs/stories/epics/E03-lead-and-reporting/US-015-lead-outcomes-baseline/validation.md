# Validation

## Proof Strategy

This story is done only when LiveLead can record manual conversion outcomes on a
lead, preserve those outcomes in timeline history with actor and timestamp
context, optionally link them to used content, and expose enough structured data
for later funnel or attribution stories without depending on CRM sync.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Allowed outcome types, contradiction guards, optional content-link validation, latest-outcome derivation, and timeline-entry creation. |
| Integration | Outcome-create endpoint behavior, lead latest-outcome read model, timeline persistence, invalid lead-state or content-link handling, and audit fields. |
| E2E | User opens a lead, records a contact or meeting outcome, sees it appear in timeline history, and optionally links it to previously used content. |
| Platform | Story verify command keeps backend outcome behavior and frontend lead-outcome flows wired into the Harness matrix. |
| Performance | Lead detail and timeline queries remain responsive with realistic mixed activity and outcome histories. |
| Logs/Audit | Outcome creation and rejection events remain diagnosable with lead id, actor, outcome type, linked content id when present, and occurred-at time. |

## Fixtures

- One lead fixture ready for a first contact outcome.
- One lead fixture with previously used content available for optional linkage.
- One lead fixture that should reject an incompatible outcome attempt.
- Deterministic users for sales and analyst roles when outcome visibility differs
  in UI proof.

## Commands

```text
- ./scripts/verify-us-015.sh — story verification chain for lead-outcome unit/integration/e2e coverage
- frontend/e2e/lead-outcomes.spec.ts — browser proof for manual outcome recording
```

## Acceptance Evidence

- `tests/unit/test_lead_outcomes.py` — outcome rules and latest-outcome derivation
- `tests/integration/test_lead_outcomes_api.py` — outcome persistence, validation, and timeline read model
- Lead detail or pipeline UI outcome action with timeline visibility
- `scripts/bin/harness-cli story verify US-015` — pass after the verify command is added
