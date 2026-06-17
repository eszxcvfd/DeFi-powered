# Design

## Domain Model

The first i18n and timezone baseline slice formalizes
the durable objects and bounded services that turn
`NFR-I18N-001`, `NFR-I18N-002`, and `NFR-I18N-003` into
a documented contract, a closed `Locale` enum, a
bounded `Timezone` validation, a per-user and
per-organization locale/timezone surface, a reusable
React hook and component, a minimum-viable dictionary,
and a bounded verification command.

### `Locale` (closed enum)

A closed enumeration of supported locales. The
bounded surfaces read from and reject any value
outside the closed set with `LOCALE_UNSUPPORTED`. New
locales cannot be added without first extending the
`I18nService`, the dictionary loader, and the audit
entry shape.

- `vi-VN` — Vietnamese (Vietnam). 24-hour
  `dd/MM/yyyy HH:mm`.
- `en-US` — English (United States). 12-hour
  `MM/dd/yyyy, h:mm a`.

The default locale is `en-US` when no user-selected
or organization default value is present.

### `Timezone` (bounded IANA value type)

A bounded IANA tz database validation that the API
and UI use to validate the `users.timezone` and
`organizations.default_timezone` columns. The
bounded validation rejects abbreviations, offsets,
and values that are not in the IANA tz database with
`TIMEZONE_INVALID`.

The default timezone is `UTC` when no user-selected
or organization default value is present.

### `I18nService`

A bounded service that owns the locale and timezone
resolution, the datetime formatting, and the parsers.
The service is the only place in the product that
reads or writes a `Locale` or `Timezone` value.

- `resolve_locale(user, organization) -> Locale` —
  resolves the effective locale from `user.locale`
  first, then `organization.default_locale`, then
  `default_locale` (`en-US`).
- `resolve_timezone(user, organization) -> Timezone` —
  resolves the effective timezone from
  `user.timezone` first, then
  `organization.default_timezone`, then
  `default_timezone` (`UTC`).
- `format_datetime(dt, locale, timezone) -> str` —
  formats a stored UTC datetime in the resolved
  timezone using a closed locale formatter that
  respects the closed locale set. The first slice
  ships `vi-VN` (24-hour `dd/MM/yyyy HH:mm`) and
  `en-US` (12-hour `MM/dd/yyyy, h:mm a`).
- `format_date(dt, locale, timezone) -> str` and
  `format_time(dt, locale, timezone) -> str` —
  closed locale-aware variants for the date and
  time portions of a stored datetime.
- `parse_user_locale(value) -> Locale` and
  `parse_user_timezone(value) -> Timezone` —
  bounded parsers that reject unsupported values at
  the API boundary before they reach domain or
  application code.

### `users.locale` and `users.timezone`

A new durable `users.locale` column and a new durable
`users.timezone` column on the existing `users`
table. The columns carry the user-selected locale
and timezone; they do not influence the storage
format of any other datetime field.

### `organizations.default_locale` and `organizations.default_timezone`

A new durable `organizations.default_locale` column
and a new durable `organizations.default_timezone`
column on the existing `organizations` table. The
columns carry the organization default locale and
timezone; they do not influence the storage format
of any other datetime field.

## Application Flow

- `ResolveLocaleFromContext` reads the current user
  and the current organization, calls
  `I18nService.resolve_locale`, and returns the
  resolved `Locale` for downstream consumers.
- `ResolveTimezoneFromContext` reads the current
  user and the current organization, calls
  `I18nService.resolve_timezone`, and returns the
  resolved `Timezone` for downstream consumers.
- `UpdateUserLocale` updates the current user's
  `locale` and `timezone` columns, validates the
  values through the `I18nService` parsers, and
  emits a `user.locale.updated` audit entry.
- `UpdateOrganizationLocale` updates the
  organization `default_locale` and
  `default_timezone` columns, validates the values
  through the `I18nService` parsers, and emits an
  `organization.locale.updated` audit entry.
- `NormalizeUnicodeForSearch` applies Unicode
  normalization (NFC) to `vi-VN` search queries so
  diacritics and tone marks match consistently.

## Interface Contract

Backend contract should minimally support:

- `GET /me/locale` — current user. Returns the
  effective locale and timezone resolved through
  `I18nService.resolve_locale` and
  `I18nService.resolve_timezone`.
- `PATCH /me/locale` — current user. Body shape:
  `{ locale?: Locale, timezone?: Timezone }`.
  Emits a `user.locale.updated` audit entry on
  success.
- `GET /admin/organizations/{id}/locale` —
  owner/admin only. Returns the organization
  default locale and timezone.
- `PATCH /admin/organizations/{id}/locale` —
  owner/admin only. Body shape:
  `{ default_locale?: Locale, default_timezone?: Timezone }`.
  Emits an `organization.locale.updated` audit
  entry on success.

Expected payload concerns:

- All API datetime fields stay in UTC ISO-8601
  in the wire format. Locale and timezone
  resolution happens at the API boundary through
  the `I18nService` so the existing REST contract
  is not redefined.
- The API rejects `locale` values that are not
  in the closed set with `LOCALE_UNSUPPORTED`.
  The API rejects `timezone` values that are
  not in the IANA tz database or that the
  closed set disallows with `TIMEZONE_INVALID`.
- Cross-tenant access must remain denied or
  invisible; a user from another organization
  must not fetch or mutate the first
  organization's default locale or timezone
  through the new endpoints.

## Data Model

- Add a durable `users.locale` column and a
  durable `users.timezone` column on the existing
  `users` table, with bounded migration
  validation.
- Add a durable `organizations.default_locale`
  column and a durable
  `organizations.default_timezone` column on the
  existing `organizations` table, with the same
  bounded migration validation.
- The migration is forward-safe and has a
  rollback plan. The migration adds the four
  columns with `NOT NULL DEFAULT 'en-US'` and
  `NOT NULL DEFAULT 'UTC'` respectively. The
  migration is exercised by the verify script
  so a missing column fails the platform check,
  not just the data check.
- The migration does not weaken the existing
  audit retention guarantee from `NFR-SEC-008`
  (≥ 90 days) or the existing audit entry shape
  from `US-026`.
- Reuse existing user and organization
  identifiers and auth scope rather than
  copying user or organization snapshots into
  separate locale storage.
- Preserve room for future per-tenant locale,
  additional languages, RTL layout, currency
  localization, or external translation
  services without redefining baseline
  ownership rules.

## UI / Platform Impact

- A locale switcher on the user menu for the
  per-user `locale` and `timezone` settings.
  The switcher is a small dropdown that changes
  the locale and timezone of the current
  session through `PATCH /me/locale`.
- An admin surface on the organization settings
  page for the `default_locale` and
  `default_timezone` fields. The surface is
  gated by owner/admin role and writes through
  `PATCH /admin/organizations/{id}/locale`.
- A `useLocale()` hook that consumes the
  `I18nService` and exposes the resolved locale
  and timezone. The hook is the only way the
  existing React surfaces read the locale and
  timezone.
- A `<LocalizedDatetime>` component that
  consumes the `useLocale()` hook and replaces
  every inline `new Date(...).toLocaleString()`
  call. The component is the only way the
  existing React surfaces render a stored
  datetime.
- A `<LocalizedDate>` and `<LocalizedTime>`
  component for the date and time portions of a
  stored datetime.
- A `text_catalog` JSON dictionary under
  `frontend/src/locales/{locale}.json` for
  every user-visible string in the
  minimum-viable surface. The dictionary is
  loaded once per session and falls back to
  `en-US` when a key is missing in `vi-VN`.

## Observability

- Record audit entries for
  `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected` with the
  secret-safe payload contract from `US-026`
  and `US-041`.
- Emit structured diagnostics for locale
  switch, organization default locale
  update, `LOCALE_UNSUPPORTED` rejection,
  `TIMEZONE_INVALID` rejection, and Unicode
  normalization for `vi-VN` search queries.
- Preserve correlation between locale
  change, user or organization id, and
  the resulting audit entry.

## Alternatives Considered

1. Use a heavy i18n library (FormatJS, Lingui,
   or react-intl) and add a CI gate for missing
   keys from day one. Rejected because the
   first slice ships a minimum-viable surface;
   a future story can introduce a heavier
   library behind the same `I18nService`
   seam.
2. Persist the timezone as an offset instead of
   an IANA name. Rejected because offsets
   cannot resolve daylight saving transitions,
   and the existing audit log from `US-026`
   requires time-stable values.
3. Add per-tenant locale and per-tenant
   timezone in this slice. Rejected because
   the first slice ships one
   `default_locale` and one
   `default_timezone` per organization;
   per-tenant tuning is an explicit
   follow-on story.
4. Use the Accept-Language header for the
   locale. Rejected because the header is not
   stable across sessions and not enforceable;
   the closed `Locale` enum is the source of
   truth.
5. Translate the entire UI in this slice.
   Rejected because the first slice ships a
   minimum-viable surface; translating the
   entire UI is a follow-on story.
