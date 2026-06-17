# Internationalization And Timezone Runbook

Source: `docs/product/internationalization-and-timezone.md`,
`docs/decisions/0025-internationalization-and-timezone-baseline.md`,
and the `US-047` story packet under
`docs/stories/epics/E05-hardening/US-047-internationalization-and-timezone-baseline/`.

## When To Use This Runbook

Operators reach for this runbook when a user reports:

- A missing locale. The user-visible string renders in
  English even though the user has selected `vi-VN`.
  This is expected behaviour for keys that are not in
  the `vi-VN` dictionary; the runbook explains how to
  add a new key.
- A wrong timezone. The `<LocalizedDatetime>` component
  renders the stored UTC datetime in the wrong
  timezone. This is usually a per-user or
  per-organization default; the runbook explains how
  to update the value.
- A `locale.unsupported.rejected` audit entry. The
  audit log shows that the API or UI rejected a locale
  or timezone value that the closed set or IANA
  validation disallows. The runbook explains how to
  read the audit entry and what to do next.

## Surface Map

The i18n and timezone surface reuses the existing
audit, organization, and user surfaces from
`US-026`, `US-027`, and `US-028`:

- Per-user locale and timezone: `PATCH /me/locale` and
  the locale switcher on the user menu.
- Per-organization default locale and timezone:
  `PATCH /admin/organizations/{id}/locale` and the
  admin surface on the organization settings page.
- Audit entries:
  `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected`.

## Operator Actions

### User reports a missing locale

1. Open the audit log from `US-026` and confirm that
   the user has not been migrated to the bounded
   `users.locale` value. The migration in `US-047`
   sets `users.locale` to `en-US` by default.
2. Open the user record in the admin surface and
   confirm the `users.locale` value.
3. Open the `frontend/src/locales/{locale}.json`
   dictionary and confirm the missing key.
4. If the key is missing, add it to the dictionary
   and follow the bounded `verify-us-047.sh` flow to
   re-run the proof ladder.
5. If the key is present, the `useLocale()` hook
   might be falling back to `en-US`. Open the browser
   console and confirm the `locale.missing_key`
   warning.

### User reports a wrong timezone

1. Open the audit log from `US-026` and confirm that
   the user has not been migrated to the bounded
   `users.timezone` value. The migration in `US-047`
   sets `users.timezone` to `UTC` by default.
2. Open the user record in the admin surface and
   confirm the `users.timezone` value.
3. Open the user record through `GET /me/locale` and
   confirm the resolved timezone.
4. If the timezone is wrong, ask the user to update
   it through the locale switcher on the user menu.
5. If the user does not have access to the user menu,
   update the value through `PATCH /me/locale` with
   an admin or owner session.

### Audit log shows `locale.unsupported.rejected`

1. Open the audit entry and confirm the requested
   value, the resolved value, and the rejection code
   (`LOCALE_UNSUPPORTED` or `TIMEZONE_INVALID`).
2. If the rejection code is `LOCALE_UNSUPPORTED`, the
   requested value is not in the closed `Locale` enum.
   The audit log entry includes the requested value
   (sanitized). Add the value to the closed set as a
   follow-up story; do not edit the enum inline.
3. If the rejection code is `TIMEZONE_INVALID`, the
   requested value is not in the IANA tz database.
   The audit log entry includes the requested value
   (sanitized). Ask the user to pick a valid IANA
   name; do not edit the bounded validation inline.

## Health Probe

The new endpoints are covered by the health probe
contract from `US-040`: a missing or failing
`GET /me/locale` must not fail `GET /health/ready`,
only surface as a degraded warning. Operators see the
degraded warning on the `US-040` launch-gate
dashboard.

## Follow-Up

- Per-tenant locale and per-tenant timezone tuning
  behind the same `I18nService` seam.
- Additional languages (e.g., `ja-JP`, `ko-KR`,
  `zh-CN`) behind the same `Locale` enum and
  dictionary loader.
- A CI gate for missing keys that turns the
  `locale.missing_key` warning into a hard build
  failure.
- Currency, number, and measurement localization
  behind the same `I18nService` seam.
- Right-to-left (RTL) layout support behind the
  same `Locale` enum.
- External translation services (DeepL, Google
  Translate, a managed TMS) behind the same
  `I18nService` seam.
- Audit log or analytics export of per-user locale
  and timezone.
- Per-locale A/B test instrumentation behind the
  same `I18nService` seam.
