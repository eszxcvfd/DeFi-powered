# Validation

## Proof Strategy

This story is done only when LiveLead can load a date-range dashboard overview,
show trustworthy summary widgets from existing workflow data, expose freshness
for each widget, and tell the user when a metric is empty versus unavailable
without depending on later funnel or export stories.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Time-window normalization, metric availability classification, zero-versus-unavailable rules, and freshness derivation. |
| Integration | Dashboard aggregation endpoint, cross-domain widget composition, invalid-range handling, and unavailable-widget payload behavior. |
| E2E | User opens dashboard, changes the time range, sees populated cards when fixture data exists, and sees explicit empty or unavailable states when it does not. |
| Platform | Story verify command keeps backend reporting queries and frontend dashboard rendering wired into the Harness matrix. |
| Performance | Dashboard overview queries remain responsive for realistic seeded event, content, lead, and reminder counts without hidden fan-out regressions. |
| Logs/Audit | Dashboard requests remain diagnosable with time window, widget key, freshness, and availability status context. |

## Fixtures

- Seeded event records across more than one observation date.
- Seeded scored or prioritized events within and outside the selected time
  window.
- Seeded content lifecycle records for created, approved, or used counts.
- Seeded lead and reminder records that exercise both populated and empty
  widgets.
- At least one metric fixture intentionally left without durable source truth so
  unavailable-state behavior can be proven honestly.

## Commands

```text
- ./scripts/verify-us-014.sh — story verification chain for dashboard unit/integration/e2e coverage
- frontend/e2e/dashboard-overview.spec.ts — dashboard browser proof
```

## Acceptance Evidence

- `tests/unit/test_dashboard_overview.py` — time-window, availability, and freshness rules
- `tests/integration/test_dashboard_overview_api.py` — widget aggregation and payload behavior
- Dashboard overview route or section with date-range controls and widget freshness labels
- `scripts/bin/harness-cli story verify US-014` — pass after the verify command is added
