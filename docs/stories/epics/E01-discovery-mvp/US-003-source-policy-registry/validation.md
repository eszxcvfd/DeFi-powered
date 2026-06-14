# Validation

## Proof Strategy

This story is done only when LiveLead can prove that source governance exists
before connector execution, that denied policy states are explainable, and that
secret-safe behavior is preserved across admin and backend flows.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Policy evaluation for enabled/disabled, approval, time-window, and budget states; secret-redaction helpers; API/feed preference selection rules. |
| Integration | Persistence + API tests for create/list/detail/update registry flows, approval metadata, secret storage reference handling, and denied-runnable state transitions. |
| E2E | Admin manages source records in the UI, sees blocked/runnable state, and never sees raw secret values. |
| Platform | Story verify command updates Harness matrix and keeps frontend/backend checks runnable in local MVP tooling. |
| Performance | Not a primary gate; confirm registry queries remain bounded for normal admin listing. |
| Logs/Audit | Policy-denied and secret-related flows produce safe diagnostic records without plaintext secret leakage. |

## Fixtures

- One organization with an admin user.
- At least three deterministic source fixtures:
  - Official API or RSS source that should be preferred.
  - Browser-only source that is approved but subject to policy checks.
  - Disabled or over-budget source that must be denied.
- Secret fixture values suitable for redaction assertions.

## Commands

Add commands after scripts exist.

```text
./scripts/verify-us-003.sh
```

## Acceptance Evidence

- `./scripts/verify-us-003.sh` — policy unit tests, admin API + secret redaction, Playwright admin + wizard sources step.
