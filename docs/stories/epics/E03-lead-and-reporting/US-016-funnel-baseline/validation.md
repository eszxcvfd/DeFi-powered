# Validation

## Proof Strategy

This story is done only when LiveLead can load a funnel report for a selected
cohort, show ordered steps from event to lead to contact to response to meeting
to opportunity using durable lead-outcome data, explain freshness, and surface
manual-lead or unattributed caveats without depending on source-performance or
export stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Cohort normalization, step-count derivation, manual-lead handling, and freshness rules. |
| Integration | `GET /reports/funnel` behavior across event-linked leads, manual leads, and explicit outcome data; invalid-range handling; and ordered step payload validation. |
| E2E | User opens the funnel report, changes the selected window, sees ordered step counts, and understands any empty or unattributed states that appear. |
| Platform | Story verify command keeps backend funnel reporting and frontend funnel rendering wired into the Harness matrix. |
| Performance | Funnel queries remain responsive for realistic seeded event, lead, and outcome counts without hidden fan-out regressions. |
| Logs/Audit | Funnel requests remain diagnosable with cohort rule, ordered step counts, freshness, and unattributed-lead metadata when present. |

## Fixtures

- Seeded event-linked leads that progress through contact, response, meeting, and
  opportunity outcomes.
- Seeded manual leads without event linkage to exercise unattributed handling.
- A selected cohort with no matching conversions for empty-state proof.
- Deterministic outcome timestamps across more than one reporting window.

## Commands

```text
- ./scripts/verify-us-016.sh — story verification chain for funnel unit/integration/e2e coverage
- frontend/e2e/funnel-report.spec.ts — browser proof for funnel reporting
```

## Acceptance Evidence

- `tests/unit/test_funnel_reporting.py` — cohort and step derivation rules
- `tests/integration/test_funnel_reporting_api.py` — funnel payloads and manual-lead handling
- Funnel report UI with ordered steps and freshness metadata
- `scripts/bin/harness-cli story verify US-016` — pass after the verify command is added
