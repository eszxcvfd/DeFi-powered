# Validation

## Proof Strategy

This story is done only when LiveLead can load a grouped source-performance
report for a selected time range, switch between platform, connector, campaign,
and industry groupings, show attributable metrics from durable source-linked
records, and explain freshness and unattributed states without depending on
content-effectiveness or export stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Grouping normalization, source-attribution rules, unattributed handling, and freshness derivation. |
| Integration | Source-performance endpoint behavior across platform, connector, campaign, and industry groupings; invalid-group handling; and grouped metric payload validation. |
| E2E | User opens source-performance reporting, changes the grouping dimension, sees grouped rows update, and understands any empty or unattributed states that appear. |
| Platform | Story verify command keeps backend grouped reporting and frontend source-performance rendering wired into the Harness matrix. |
| Performance | Grouped source-performance queries remain responsive for realistic seeded event, lead, and outcome counts across all supported grouping keys. |
| Logs/Audit | Source-performance requests remain diagnosable with time window, grouping key, row count, freshness, and unattributed metrics when present. |

## Fixtures

- Seeded source-linked events across more than one platform and connector.
- Seeded campaigns across more than one industry with linked leads and outcomes.
- Seeded records missing one grouping dimension to exercise unattributed
  handling.
- A selected reporting window with no matching records for empty-state proof.

## Commands

```text
- ./scripts/verify-us-017.sh — story verification chain (verify-us-016 + unit/integration + e2e)
- frontend/e2e/source-performance.spec.ts — browser proof for grouped source reporting
```

## Acceptance Evidence

- `tests/unit/test_source_performance_reporting.py` — grouping and attribution rules
- `tests/integration/test_source_performance_reporting_api.py` — grouped payloads and invalid-group handling
- Source-performance report UI with grouping controls and freshness metadata
- `scripts/bin/harness-cli story verify US-017` — pass
