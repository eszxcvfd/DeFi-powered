# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `I18nService.resolve_locale` reads the user locale first, then the organization default locale, then the `default_locale` (`en-US`). `I18nService.resolve_timezone` reads the user timezone first, then the organization default timezone, then the `default_timezone` (`UTC`). `I18nService.format_datetime` formats a stored UTC datetime in the resolved timezone using a closed locale formatter that respects the closed locale set. `I18nService.parse_user_locale` rejects any value outside the closed `Locale` enum with `LOCALE_UNSUPPORTED`. `I18nService.parse_user_timezone` rejects any value outside the IANA tz database with `TIMEZONE_INVALID`. The closed `Locale` enum is closed; unknown locales return `LOCALE_UNSUPPORTED`. The `useLocale()` hook returns the resolved locale and timezone. The `<LocalizedDatetime>` component renders a stored UTC datetime in the resolved timezone using the closed locale formatter. `NormalizeUnicodeForSearch` applies Unicode normalization (NFC) to `vi-VN` search queries. |
| Integration | `GET /me/locale` returns the effective locale and timezone resolved through `I18nService.resolve_locale` and `I18nService.resolve_timezone`. `PATCH /me/locale` updates the current-user locale and timezone, validates the values through the `I18nService` parsers, and emits a `user.locale.updated` audit entry. `GET /admin/organizations/{id}/locale` returns the organization default locale and timezone. `PATCH /admin/organizations/{id}/locale` updates the organization default locale and timezone, validates the values through the `I18nService` parsers, and emits an `organization.locale.updated` audit entry. The API rejects unsupported locale values with `LOCALE_UNSUPPORTED` and unsupported timezone values with `TIMEZONE_INVALID`. The migration adds the four columns (`users.locale`, `users.timezone`, `organizations.default_locale`, `organizations.default_timezone`) with `NOT NULL DEFAULT 'en-US'` and `NOT NULL DEFAULT 'UTC'`. Every locale and timezone change emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. |
| E2E | An authenticated user can open the new locale switcher, switch between `vi-VN` and `en-US`, switch between two timezones, and see the `<LocalizedDatetime>` component render the stored datetime in the resolved timezone. An authenticated owner/admin can open the new organization locale surface, change the `default_locale` and `default_timezone`, and see the change reflected for the current user. The bounded verification harness runs a deterministic i18n flow for a seeded user and organization, asserts the recorded settings stay within the contract, and exercises the `LOCALE_UNSUPPORTED` and `TIMEZONE_INVALID` rejection paths. The migration is exercised end-to-end by the verify script so a missing `users.locale` or `users.timezone` column fails the E2E check, not just the data check. The Unicode normalization for `vi-VN` search queries is exercised end-to-end by a search query that includes diacritics and tone marks. |
| Security | Direct API calls to `PATCH /me/locale` with another user's session are rejected with the same error envelope as the existing user surfaces. Direct API calls to `PATCH /admin/organizations/{id}/locale` with viewer, analyst, sales, or reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Cross-tenant access to `GET /admin/organizations/{id}/locale` and `PATCH /admin/organizations/{id}/locale` is rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that audit entries carrying the previous and new locale or timezone are sanitized before persistence. The bounded `Timezone` validation rejects abbreviations, offsets, and values that are not in the IANA tz database. The closed `Locale` enum does not weaken the existing `ConnectorHealthStatus` enum from `US-046`, the existing `MetricRegistry` from `US-042`, the existing `AlertMetric` enum from `US-041`, or the existing audit retention guarantee from `NFR-SEC-008` (≥ 90 days). |
| Operational | A runbook entry for the i18n and timezone domain documents what an operator does when a user reports a missing locale, when a user reports a wrong timezone, and when the audit log shows a `locale.unsupported.rejected` rejection. The verification script proves that the bounded verification harness can run a deterministic i18n flow for a seeded user and organization and assert the recorded settings stay within the contract. The new endpoints are covered by the health probe contract from `US-040`: a missing or failing `GET /me/locale` must not fail `GET /health/ready`, only surface as a degraded warning. |
| Platform | The `scripts/verify-us-047.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The migration is exercised by the verify script so a missing column fails the platform check, not just the data check. The new closed `Locale` enum, the new bounded `Timezone` validation, the new `I18nService` operations, the new audit entry types, and the new dictionary loader are exercised by the verify script so a missing enum value or a missing service operation fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `I18nService.resolve_locale`
  - `I18nService.resolve_timezone`
  - `I18nService.format_datetime`
  - `I18nService.format_date`
  - `I18nService.format_time`
  - `I18nService.parse_user_locale`
  - `I18nService.parse_user_timezone`
  - `Locale` enum closure
  - `Timezone` bounded validation
  - `NormalizeUnicodeForSearch` for `vi-VN`
- Backend integration tests for:
  - `GET /me/locale`
  - `PATCH /me/locale`
  - `GET /admin/organizations/{id}/locale`
  - `PATCH /admin/organizations/{id}/locale`
  - Cross-tenant denial for every new endpoint
  - Audit entries for every successful and
    failed locale and timezone change
  - `LOCALE_UNSUPPORTED` rejection path
  - `TIMEZONE_INVALID` rejection path
- E2E tests for:
  - Locale switcher changes the user menu,
    the `<LocalizedDatetime>` component, and
    the dictionary fallback.
  - Admin organization locale surface changes
    the `default_locale` and
    `default_timezone` and reflects the change
    for the current user.
  - Bounded verification harness runs a
    deterministic i18n flow and asserts the
    recorded settings stay within the contract.
  - The migration is exercised end-to-end by
    the verify script.
  - Unicode normalization for `vi-VN` search
    queries is exercised end-to-end.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Audit entry sanitization for every new
    write path.
  - Cross-tenant denial for every new
    endpoint.
  - `LOCALE_UNSUPPORTED` and
    `TIMEZONE_INVALID` rejection paths.
- Operational checks for:
  - The bounded verification harness can run
    a deterministic i18n flow and assert the
    recorded settings stay within the
    contract.
  - The new endpoints are covered by the
    health probe contract from `US-040`.
  - The runbook entry exists and references
    the right surfaces.
- Platform proof is the
  `scripts/verify-us-047.sh` command wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_i18n_service.py` —
  `I18nService` unit tests
- `tests/unit/test_locale_enum.py` — `Locale`
  enum closure
- `tests/unit/test_timezone_validation.py` —
  `Timezone` bounded validation
- `tests/unit/test_i18n_unicode_normalization.py`
  — `NormalizeUnicodeForSearch` for `vi-VN`
- `tests/integration/test_me_locale_api.py` —
  `GET /me/locale` and `PATCH /me/locale`
  integration tests
- `tests/integration/test_admin_organization_locale_api.py`
  — `GET /admin/organizations/{id}/locale` and
  `PATCH /admin/organizations/{id}/locale`
  integration tests
- `tests/integration/test_locale_audit.py` —
  audit entry integration tests for
  `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected`
- `tests/integration/test_locale_migration.py`
  — migration forward-safety and rollback
  integration tests
- `tests/security/test_locale_role_gates.py` —
  role enforcement and cross-tenant denial
  security tests
- `tests/security/test_locale_audit_sanitizer.py`
  — audit entry sanitization security tests
- `frontend/e2e/locale-switcher.spec.ts` —
  locale switcher E2E
- `frontend/e2e/admin-organization-locale.spec.ts`
  — admin organization locale surface E2E
- `frontend/e2e/localized-datetime.spec.ts` —
  `<LocalizedDatetime>` component E2E
- `frontend/e2e/locale-unicode-search.spec.ts`
  — Unicode normalization for `vi-VN` search
  queries E2E
- `scripts/verify-us-047.sh` — bounded
  verification harness

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix`
  reports `US-047` once implemented with the
  expected proof columns populated.
- A representative e2e run covers the locale
  switcher, the admin organization locale
  surface, the `<LocalizedDatetime>` component
  rendering for both `vi-VN` and `en-US`, and
  the deterministic `verify-us-047.sh`
  command that runs the full proof ladder.
- Integration proof confirms another
  authenticated user cannot mutate or view the
  first user's locale or timezone through the
  new endpoints.
- Integration proof confirms a user from
  another organization cannot fetch or mutate
  the first organization's default locale or
  timezone through the new admin endpoints.
- Security proof confirms the
  `SanitizeAlertPayload` helper from `US-041`
  runs on every audit entry before persistence.
- Platform proof confirms the
  `scripts/verify-us-047.sh` command runs the
  full proof ladder and is wired into
  `harness-cli story verify` and
  `harness-cli story verify-all`.
