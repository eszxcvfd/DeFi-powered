# Validation

## Proof Strategy

This story is done only when LiveLead can load a grouped content-effectiveness
report for a selected time range, switch between content type, tone, and
template metadata groupings, show attributable metrics from used content and
linked outcomes, and explain freshness and unattributed states without
depending on export stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Grouping normalization, attribution rules, incomplete metadata handling, and freshness derivation. |
| Integration | Content-effectiveness endpoint behavior across content type, tone, and template groupings; invalid-group handling; and grouped metric payload validation. |
| E2E | User opens content-effectiveness reporting, changes the grouping dimension, sees grouped rows update, and understands any empty or unattributed states that appear. |
| Platform | Story verify command keeps backend grouped reporting and frontend content-effectiveness rendering wired into the Harness matrix. |
| Performance | Grouped content-effectiveness queries remain responsive for realistic seeded content, usage, and linked outcome counts across all supported grouping keys. |
| Logs/Audit | Content-effectiveness requests remain diagnosable with time window, grouping key, row count, freshness, and unattributed metrics when present. |

## Fixtures

- Seeded used content across more than one content type and tone.
- Seeded template metadata that distinguishes at least two content cohorts.
- Seeded linked outcomes for some, but not all, used content to exercise
  unattributed handling.
- A selected reporting window with no matching records for empty-state proof.

## Commands

```text
- ./scripts/verify-us-018.sh — story verification chain (verify-us-017 + unit/integration + e2e)
- frontend/e2e/content-effectiveness.spec.ts — browser proof for grouped content reporting
```

## Acceptance Evidence

- `tests/unit/test_content_effectiveness_reporting.py` — grouping and attribution rules
- `tests/integration/test_content_effectiveness_reporting_api.py` — grouped payloads and invalid-group handling
- Content-effectiveness report UI with grouping controls and freshness metadata
- `scripts/bin/harness-cli story verify US-018` — pass
