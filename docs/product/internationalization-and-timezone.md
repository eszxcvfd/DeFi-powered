# Internationalization And Timezone

Source: `SPEC.md` sections 2.5, 5.6, 5.12, 5.13, 5.14, 6.1, 8.1,
8.3, 10.6, 10.7, 11.1, 12, 14.1, and 16.

## Product Goal

LiveLead users operate across regions and write in at
least `vi-VN` and `en-US`. The product must:

- Separate every user-visible string from the code
  that renders it.
- Store datetimes in UTC and render them in the
  user-selected timezone.
- Persist a per-user `locale` and `timezone` so the
  same product behaves the same way for a Vietnamese
  analyst, an English-speaking sales user, and a
  cross-region owner.
- Preserve diacritics, normalization, and Unicode
  search behavior across the existing discovery and
  lead surfaces.

This product slice is the first bounded
internationalization and timezone baseline. It
introduces the contract that future slices will
consume when they add new surfaces or new
languages; it does not translate the entire UI.
The bounded first slice ships `vi-VN` and `en-US`
as the only two locales, the closed set of
`Locale` and `Timezone` value types, and the
`I18nService` that the rest of the codebase
consumes.

## MVP Scope

This product slice covers:

- A durable `users.locale` column and a durable
  `users.timezone` column on the existing
  `users` table, with bounded migration
  validation.
- A durable `organizations.default_locale`
  column and a durable
  `organizations.default_timezone` column on
  the existing `organizations` table, with the
  same bounded migration validation.
- A closed `Locale` enum (`vi-VN`, `en-US`) that
  the bounded surfaces read from and that the
  API and UI reject with
  `LOCALE_UNSUPPORTED` for any value outside the
  closed set.
- A closed `Timezone` value type that is
  validated against the IANA tz database and that
  the API and UI reject with `TIMEZONE_INVALID`
  for any value outside the supported set.
- A bounded `I18nService` that exposes the
  closed operations:
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
    formats a stored UTC datetime in the
    resolved timezone using a closed locale
    formatter that respects the closed locale
    set.
  - `format_date(dt, locale, timezone)` and
    `format_time(dt, locale, timezone)` —
    closed locale-aware variants for the date
    and time portions of a stored datetime.
  - `parse_user_locale(value)` and
    `parse_user_timezone(value)` — bounded
    parsers that reject unsupported values at
    the API boundary before they reach domain
    or application code.
- A new owner/admin REST surface for the
  per-user and per-organization locale and
  timezone settings:
  - `GET /me/locale` — current-user locale and
    timezone.
  - `PATCH /me/locale` — current-user locale
    and timezone upsert.
  - `GET /admin/organizations/{id}/locale` —
    owner/admin only. Returns the
    organization default locale and timezone.
  - `PATCH /admin/organizations/{id}/locale` —
    owner/admin only. Updates the organization
    default locale and timezone.
- A new frontend i18n surface:
  - A locale switcher on the user menu so a
    user can change their own `locale` and
    `timezone` without an admin role.
  - An admin surface on the organization
    settings page for the
    `default_locale` and `default_timezone`
    fields, gated by owner/admin role.
  - A reusable `useLocale()` hook that
    exposes the resolved locale and timezone
    and that the existing React surfaces
    consume.
  - A reusable `<LocalizedDatetime>` and
    `<LocalizedDate>` and `<LocalizedTime>`
    component that the existing React surfaces
    consume.
- A new `text_catalog` JSON dictionary under
  `frontend/src/locales/{locale}.json` for
  every user-visible string in the
  minimum-viable surface. The dictionary is
  loaded once per session and falls back to
  `en-US` when a key is missing in `vi-VN`.
- A new decision record
  (`docs/decisions/0025-internationalization-and-timezone-baseline.md`)
  that locks the closed `Locale` enum, the
  bounded `Timezone` validation, the API
  surface, the per-user default fallback
  order, the datetime storage rule, and the
  audit entry shape.
- A new bounded verification command
  (`scripts/verify-us-047.sh`) that runs the
  unit, integration, E2E, security, operational,
  and platform checks defined in
  `validation.md` and is wired into
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Contract Rules

- The closed `Locale` enum is the source of
  truth. Adding a new locale is an explicit
  follow-up story; the first slice ships only
  `vi-VN` and `en-US`.
- Datetime storage stays in UTC across the
  existing schema. The `I18nService.format_*`
  helpers convert to the resolved timezone at
  the API and UI boundaries.
- The API rejects `locale` values that are not
  in the closed set with `LOCALE_UNSUPPORTED`.
  The API rejects `timezone` values that are
  not in the IANA tz database or that the
  closed set disallows with `TIMEZONE_INVALID`.
- The first slice stores timezone values as
  IANA names. The bounded validation rejects
  abbreviations, offsets, and values that are
  not in the IANA tz database.
- The first slice does not translate the
  entire UI. The MVP dictionary covers the
  minimum-viable surface; missing keys fall
  back to `en-US` and emit a
  `locale.missing_key` warning that a future
  story can turn into a CI gate.
- The first slice does not change the
  existing audit retention guarantee from
  `NFR-SEC-008` (≥ 90 days) or the existing
  audit entry shape from `US-026`. Locale
  and timezone changes emit a
  `user.locale.updated` or
  `organization.locale.updated` audit entry
  with the secret-safe payload contract from
  `US-041`.
- The bounded migration is forward-safe and
  has a rollback plan. The migration is
  exercised by the verify script so a missing
  column fails the platform check, not just
  the data check.
- The closed `Locale` enum does not weaken
  the existing `ConnectorHealthStatus` enum
  from `US-046`, the existing
  `MetricRegistry` from `US-042`, the
  existing `AlertMetric` enum from `US-041`,
  or the existing audit retention guarantee
  from `NFR-SEC-008`.
- The first slice does not change the
  authentication boundary from `US-027`,
  the RBAC roles from `US-027`/`US-028`, or
  the tenant isolation contract from
  `US-027`. A user can only update their own
  locale and timezone through `PATCH /me/locale`;
  organization default locale and timezone
  updates require an owner/admin session.

## API Surface

- `GET /me/locale` — current user. Returns the
  effective locale and timezone resolved
  through `I18nService.resolve_locale` and
  `I18nService.resolve_timezone`.
- `PATCH /me/locale` — current user. Body
  shape: `{ locale?: Locale, timezone?: Timezone }`.
  Emits a `user.locale.updated` audit entry
  on success.
- `GET /admin/organizations/{id}/locale` —
  owner/admin only. Returns the organization
  default locale and timezone.
- `PATCH /admin/organizations/{id}/locale` —
  owner/admin only. Body shape:
  `{ default_locale?: Locale, default_timezone?: Timezone }`.
  Emits a `organization.locale.updated` audit
  entry on success.
- All API datetime fields stay in UTC ISO-8601
  in the wire format. Locale and timezone
  resolution happens at the API boundary
  through the `I18nService` so the existing
  REST contract is not redefined.

## Datetime Storage And Display

- All datetimes are stored in UTC across the
  existing schema. The new
  `users.timezone` and
  `organizations.default_timezone` columns
  carry the IANA name only; they do not
  influence the storage format.
- The `I18nService.format_datetime` helper
  formats a stored UTC datetime in the
  resolved timezone using a closed locale
  formatter. The first slice ships
  `vi-VN` (24-hour `dd/MM/yyyy HH:mm`) and
  `en-US` (12-hour `MM/dd/yyyy, h:mm a`) as
  the only two formats.
- The first slice preserves Unicode
  normalization for `vi-VN` search queries
  (NFC) so diacritics and tone marks match
  consistently.

## Audit Entry Contract

- `user.locale.updated` — current user updated
  their own locale or timezone. Payload
  includes the previous and new locale or
  timezone. Runs through the
  `SanitizeAlertPayload` helper from `US-041`.
- `organization.locale.updated` — owner/admin
  updated the organization default locale or
  timezone. Payload includes the previous and
  new default locale or timezone. Runs through
  the `SanitizeAlertPayload` helper from
  `US-041`.
- `locale.unsupported.rejected` — a request
  to set a locale or timezone that the closed
  set or IANA validation disallows. Payload
  includes the requested value (sanitized),
  the resolved value, and the rejection code.

## UI Surface

The first i18n slice should extend existing
admin and user surfaces:

- Locale switcher on the user menu for the
  per-user `locale` and `timezone` settings.
  The switcher is a small dropdown that
  changes the locale and timezone of the
  current session through `PATCH /me/locale`.
- Admin surface on the organization settings
  page for the `default_locale` and
  `default_timezone` fields. The surface is
  gated by owner/admin role and writes
  through `PATCH /admin/organizations/{id}/locale`.
- A `useLocale()` hook that consumes the
  `I18nService` and exposes the resolved
  locale and timezone. The hook is the only
  way the existing React surfaces read the
  locale and timezone.
- A `<LocalizedDatetime>` component that
  consumes the `useLocale()` hook and
  replaces every inline `new Date(...).toLocaleString()`
  call. The component is the only way the
  existing React surfaces render a stored
  datetime.
- A `<LocalizedDate>` and `<LocalizedTime>`
  component for the date and time portions of
  a stored datetime. The component is the
  only way the existing React surfaces
  render a stored date or time.

## Validation Implications

- Unit proof should cover the
  `I18nService.resolve_locale` and
  `I18nService.resolve_timezone` fallback
  order, the closed `Locale` enum, the
  bounded `Timezone` validation, the
  `format_datetime` formatter, the
  `parse_user_locale` and
  `parse_user_timezone` parsers, the
  `useLocale()` hook, and the
  `<LocalizedDatetime>` component.
- Integration proof should cover the REST
  surface, the audit entry shape, the
  migration forward-safety, the
  cross-tenant denial paths, the
  `LOCALE_UNSUPPORTED` and
  `TIMEZONE_INVALID` rejection paths, the
  Unicode normalization for `vi-VN` search
  queries, and the `locale.unsupported.rejected`
  audit entry.
- E2E proof should cover the locale
  switcher, the admin organization locale
  surface, the `<LocalizedDatetime>`
  component rendering for both `vi-VN` and
  `en-US`, and the deterministic
  `verify-us-047.sh` command that runs the
  full proof ladder.
- Logs or audit proof should confirm who
  updated a locale or timezone, the
  previous and new values, and when.
- Platform proof should keep the
  internationalization verification path
  wired into the Harness matrix before
  per-tenant locale, additional languages,
  or external translation services build
  on it.

## Out Of Scope

- Translating every UI string in the
  product. The first slice ships the
  minimum-viable dictionary; a future story
  can add additional languages, additional
  keys, and CI gates for missing keys.
- Datetime storage format changes. The
  first slice keeps the existing UTC
  storage contract; only the display layer
  changes.
- Per-tenant locale or per-tenant timezone
  beyond the organization default. The
  first slice ships one
  `default_locale` and one
  `default_timezone` per organization; a
  future story can extend the surface with
  per-tenant tuning without redefining the
  contract.
- Right-to-left (RTL) layout support. The
  first slice ships `vi-VN` (LTR) and
  `en-US` (LTR); RTL is an explicit
  follow-on story.
- External translation services (DeepL,
  Google Translate, a managed TMS).
- Currency, number, or measurement
  localization. The first slice ships
  locale-aware datetime formatting only;
  currency, number, and measurement
  formatting are explicit follow-on
  stories.
- Audit log or analytics export of
  per-user locale and timezone. The first
  slice records the change through the
  audit entry shape from `US-026`; a
  future story can extend the export
  surface.
