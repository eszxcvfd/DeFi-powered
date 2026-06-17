# Exec Plan

## Goal

Define and implement the first internationalization and
timezone baseline for LiveLead so the product can
separate every user-visible string from the code that
renders it, store datetimes in UTC, and render them in
the user-selected timezone, while keeping the
authentication boundary, the RBAC roles, the tenant
isolation contract, the audit entry shape, and the
audit retention guarantee intact.

## Scope

In scope:

- A durable `users.locale` column and a durable
  `users.timezone` column on the existing `users`
  table, with bounded migration validation.
- A durable `organizations.default_locale` column
  and a durable `organizations.default_timezone`
  column on the existing `organizations` table,
  with the same bounded migration validation.
- A closed `Locale` enum (`vi-VN`, `en-US`) that
  the bounded surfaces read from and that the API
  and UI reject with `LOCALE_UNSUPPORTED` for any
  value outside the closed set.
- A bounded `Timezone` value type that is
  validated against the IANA tz database and that
  the API and UI reject with `TIMEZONE_INVALID`
  for any value outside the supported set.
- A bounded `I18nService` that exposes the closed
  operations:
  - `resolve_locale(user, organization)` —
    resolves the effective locale from
    `user.locale` first, then
    `organization.default_locale`, then
    `default_locale` (`en-US`).
  - `resolve_timezone(user, organization)` —
    resolves the effective timezone from
    `user.timezone` first, then
    `organization.default_timezone`, then
    `default_timezone` (`UTC`).
  - `format_datetime(dt, locale, timezone)` —
    formats a stored UTC datetime in the resolved
    timezone using a closed locale formatter.
  - `format_date(dt, locale, timezone)` and
    `format_time(dt, locale, timezone)` — closed
    locale-aware variants for the date and time
    portions of a stored datetime.
  - `parse_user_locale(value)` and
    `parse_user_timezone(value)` — bounded
    parsers that reject unsupported values at
    the API boundary before they reach domain
    or application code.
- A new owner/admin REST surface for the per-user
  and per-organization locale and timezone
  settings:
  - `GET /me/locale` — current-user locale and
    timezone.
  - `PATCH /me/locale` — current-user locale and
    timezone upsert.
  - `GET /admin/organizations/{id}/locale` —
    owner/admin only.
  - `PATCH /admin/organizations/{id}/locale` —
    owner/admin only.
- A new frontend i18n surface:
  - A locale switcher on the user menu for the
    per-user `locale` and `timezone` settings.
  - An admin surface on the organization
    settings page for the `default_locale` and
    `default_timezone` fields, gated by
    owner/admin role.
  - A reusable `useLocale()` hook that exposes
    the resolved locale and timezone.
  - A reusable `<LocalizedDatetime>` and
    `<LocalizedDate>` and `<LocalizedTime>`
    component.
- A new `text_catalog` JSON dictionary under
  `frontend/src/locales/{locale}.json` for
  every user-visible string in the
  minimum-viable surface.
- A new product doc
  (`docs/product/internationalization-and-timezone.md`).
- A new decision record
  (`docs/decisions/0025-internationalization-and-timezone-baseline.md`).
- A new bounded verification command
  (`scripts/verify-us-047.sh`).
- Audit entries for
  `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected` with the same
  secret-safe payload contract as `US-026` and
  `US-041`.
- Unicode normalization (NFC) for `vi-VN`
  search queries so diacritics and tone marks
  match consistently.

Out of scope:

- Translating every UI string in the product.
- Datetime storage format changes. The first
  slice keeps the existing UTC storage
  contract; only the display layer changes.
- Per-tenant locale or per-tenant timezone
  beyond the organization default.
- Right-to-left (RTL) layout support.
- External translation services (DeepL, Google
  Translate, a managed TMS).
- Currency, number, or measurement
  localization.
- Audit log or analytics export of per-user
  locale and timezone.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Multi-domain.

Hard gates:

- Authentication, authorization, tenant
  isolation, audit retention, or RBAC roles
  must not be weakened by this slice.

## Work Phases

1. Discovery: confirm i18n and timezone
   requirements from `SPEC.md` (sections
   2.5, 5.6, 5.12, 5.13, 5.14, 6.1, 8.1, 8.3,
   10.6, 10.7, 11.1, 12, 14.1, and 16) and
   from the existing product docs.
2. Design: define the `Locale` enum, the
   `Timezone` value type, the `I18nService`
   interface, the migration shape, the API
   surface, the audit entry shape, the
   frontend hook and component contract, the
   dictionary loader, and the
   `locale.unsupported.rejected` rejection
   contract.
3. Validation planning: design proof for the
   `I18nService.resolve_locale` and
   `I18nService.resolve_timezone` fallback
   order, the closed `Locale` enum, the
   bounded `Timezone` validation, the
   `format_datetime` formatter, the
   `parse_user_locale` and
   `parse_user_timezone` parsers, the
   `useLocale()` hook, the
   `<LocalizedDatetime>` component, the
   Unicode normalization for `vi-VN` search
   queries, and the cross-tenant denial
   paths.
4. Implementation: add the migration, the
   `I18nService`, the closed `Locale` enum,
   the bounded `Timezone` validation, the
   API surface, the audit entry shape, the
   frontend hook and component, the
   dictionary loader, and the
   `locale.unsupported.rejected` audit
   entry.
5. Verification: prove that a Vietnamese
   user can switch the locale and timezone
   through the user menu, that an
   owner/admin can update the organization
   default locale and timezone, that the
   `<LocalizedDatetime>` component renders
   the resolved datetime in the resolved
   timezone, and that the bounded
   verification harness runs a deterministic
   i18n flow and asserts the recorded
   settings stay within the contract.
6. Harness update: keep the product docs
   current, record durable story status,
   add a decision record, and leave a clean
   handoff for per-tenant locale,
   additional languages, RTL layout,
   currency/number localization, or
   external translation services.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Authentication, authorization, tenant
  isolation, audit retention, or RBAC roles
  must change.
- Architecture direction changes.
- The team wants per-tenant locale, RTL
  layout, additional languages, currency
  localization, or external translation
  services folded into the baseline.
- The closed `Locale` enum must change
  shape.
- The bounded `Timezone` validation must
  change shape.
- The audit retention guarantee from
  `NFR-SEC-008` (≥ 90 days) must be
  weakened.
