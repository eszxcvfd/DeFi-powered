# 0025 Internationalization And Timezone Baseline

Date: 2026-06-16

## Status

Proposed (companion decision to `US-047`).

## Context

`SPEC.md` commits the product to two internationalization
and timezone requirements:

- `NFR-I18N-001` — UI must separate strings from code and
  support at least `vi-VN` and `en-US`.
- `NFR-I18N-002` — the system must store datetimes in
  UTC and render them in the user timezone.
- `NFR-I18N-003` — search must support Unicode, diacritics,
  and normalization.

LiveLead has shipped forty-six stories that all rely on
hard-coded English strings and on the system-local
`datetime.now()` / `Date#toLocaleString()` calls scattered
across the React surfaces. The product still has no
bounded i18n baseline:

- There is no closed `Locale` enum. Every translation
  request has to infer the supported set from a code
  comment, a README, or a memory of how the API was
  written.
- There is no bounded `Timezone` validation. The product
  does not even know which timezone a user is in, and the
  audit log cannot show the previous-vs-new timezone when
  a user switches.
- There is no `users.locale` column. The default locale is
  whatever the browser sends, which is not stable across
  sessions and not enforceable.
- There is no `users.timezone` column. The
  `<LocalizedDatetime>` component does not exist; every
  date or time is rendered with
  `new Date(...).toLocaleString()` and produces inconsistent
  results across regions.
- The first slice does not exist for `vi-VN` or `en-US`.
  Vietnamese strings are not even available; English
  strings are baked into the React source.

`SPEC.md` section 17 lists internationalization as part
of the production readiness review in "Giai đoạn 5 —
Hardening". The product cannot reach that milestone
without a bounded i18n and timezone baseline.

The next step is therefore a bounded i18n and timezone
slice that turns `NFR-I18N-001` and `NFR-I18N-002` into a
documented contract, a closed `Locale` enum, a bounded
`Timezone` validation, a per-user and per-organization
locale/timezone surface, a reusable React hook and
component, a minimum-viable dictionary, and a bounded
verification command. The slice is the foundation for
production readiness and for future language expansion.

## Decision

`US-047` introduces the first bounded
internationalization and timezone baseline for LiveLead.

### Domain objects

- **`Locale`** — closed enum (`vi-VN`, `en-US`) that
  the bounded surfaces read from. Adding a new locale
  is an explicit follow-up story; the first slice ships
  only the two values above.
- **`Timezone`** — bounded IANA tz database validation
  that the API and UI use to validate the
  `users.timezone` and
  `organizations.default_timezone` columns.
- **`I18nService`** — bounded service that owns the
  locale/timezone resolution, the datetime formatting,
  and the parsers. The service is the only place in the
  product that reads or writes a `Locale` or `Timezone`
  value.
- **`users.locale`** — durable column on the existing
  `users` table that carries the user-selected locale.
- **`users.timezone`** — durable column on the existing
  `users` table that carries the user-selected IANA
  timezone.
- **`organizations.default_locale`** — durable column
  on the existing `organizations` table that carries
  the organization default locale.
- **`organizations.default_timezone`** — durable column
  on the existing `organizations` table that carries
  the organization default IANA timezone.

### API contract

- `GET /me/locale` — current user. Returns the
  effective locale and timezone resolved through
  `I18nService.resolve_locale` and
  `I18nService.resolve_timezone`.
- `PATCH /me/locale` — current user. Body shape:
  `{ locale?: Locale, timezone?: Timezone }`. Emits
  a `user.locale.updated` audit entry on success.
- `GET /admin/organizations/{id}/locale` —
  owner/admin only. Returns the organization default
  locale and timezone.
- `PATCH /admin/organizations/{id}/locale` —
  owner/admin only. Body shape:
  `{ default_locale?: Locale, default_timezone?: Timezone }`.
  Emits a `organization.locale.updated` audit entry
  on success.

All API datetime fields stay in UTC ISO-8601 in the wire
format. Locale and timezone resolution happens at the
API boundary through the `I18nService` so the existing
REST contract is not redefined.

### Audit entry shape

The audit entry shape reuses the existing
`AuditService` from `US-026`:

- `user.locale.updated` — current user updated
  their own locale or timezone. Payload includes
  the previous and new locale or timezone. Runs
  through the `SanitizeAlertPayload` helper from
  `US-041`.
- `organization.locale.updated` — owner/admin
  updated the organization default locale or
  timezone. Payload includes the previous and new
  default locale or timezone. Runs through the
  `SanitizeAlertPayload` helper from `US-041`.
- `locale.unsupported.rejected` — a request to
  set a locale or timezone that the closed set
  or IANA validation disallows. Payload includes
  the requested value (sanitized), the resolved
  value, and the rejection code.

### Frontend contract

- A `useLocale()` hook that consumes the
  `I18nService` and exposes the resolved locale
  and timezone. The hook is the only way the
  existing React surfaces read the locale and
  timezone.
- A `<LocalizedDatetime>` component that consumes
  the `useLocale()` hook and replaces every inline
  `new Date(...).toLocaleString()` call. The
  component is the only way the existing React
  surfaces render a stored datetime.
- A `<LocalizedDate>` and `<LocalizedTime>`
  component for the date and time portions of a
  stored datetime.
- A `text_catalog` JSON dictionary under
  `frontend/src/locales/{locale}.json` for every
  user-visible string in the minimum-viable
  surface. The dictionary is loaded once per
  session and falls back to `en-US` when a key
  is missing in `vi-VN`.

### Migration

- The migration is forward-safe and has a rollback
  plan. The migration adds the four columns
  (`users.locale`, `users.timezone`,
  `organizations.default_locale`,
  `organizations.default_timezone`) with
  `NOT NULL DEFAULT 'en-US'` and
  `NOT NULL DEFAULT 'UTC'` respectively. The
  migration is exercised by the verify script
  so a missing column fails the platform check,
  not just the data check.
- The migration does not weaken the existing
  audit retention guarantee from `NFR-SEC-008`.

### Boundary rules

- The closed `Locale` enum is the source of
  truth. Adding a new locale is an explicit
  follow-up story; the first slice ships only
  `vi-VN` and `en-US`.
- The API rejects `locale` values that are not
  in the closed set with `LOCALE_UNSUPPORTED`.
  The API rejects `timezone` values that are
  not in the IANA tz database or that the
  closed set disallows with `TIMEZONE_INVALID`.
- All datetimes are stored in UTC across the
  existing schema. The new
  `users.timezone` and
  `organizations.default_timezone` columns
  carry the IANA name only; they do not
  influence the storage format.
- The first slice does not change the
  authentication boundary from `US-027`, the
  RBAC roles from `US-027`/`US-028`, or the
  tenant isolation contract from `US-027`. A
  user can only update their own locale and
  timezone through `PATCH /me/locale`;
  organization default locale and timezone
  updates require an owner/admin session.

## Alternatives Considered

1. Use a heavy i18n library (FormatJS, Lingui, or
   react-intl) and add a CI gate for missing keys
   from day one. Rejected because the first slice
   ships a minimum-viable surface; a future story
   can introduce a heavier library behind the same
   `I18nService` seam.
2. Persist the timezone as an offset instead of an
   IANA name. Rejected because offsets cannot
   resolve daylight saving transitions, and the
   existing audit log from `US-026` requires
   time-stable values.
3. Add per-tenant locale and per-tenant timezone
   in this slice. Rejected because the first
   slice ships one `default_locale` and one
   `default_timezone` per organization; per-tenant
   tuning is an explicit follow-on story.
4. Use the Accept-Language header for the locale.
   Rejected because the header is not stable across
   sessions and not enforceable; the closed
   `Locale` enum is the source of truth.
5. Translate the entire UI in this slice.
   Rejected because the first slice ships a
   minimum-viable surface; translating the
   entire UI is a follow-on story.

## Consequences

Positive:

- The product contract is now explicit. The
  closed `Locale` enum, the bounded
  `Timezone` validation, the per-user and
  per-organization locale/timezone surface,
  the audit entry shape, and the dictionary
  loader are documented and enforceable.
- The first slice enables Vietnamese-speaking
  users to use LiveLead in their language and
  timezone without an admin role.
- The first slice preserves Unicode
  normalization for `vi-VN` search queries
  (NFC) so diacritics and tone marks match
  consistently.
- The first slice does not redefine the
  authentication boundary, the RBAC roles, or
  the tenant isolation contract from
  `US-027`/`US-028`. A user can only update
  their own locale and timezone through
  `PATCH /me/locale`; organization default
  locale and timezone updates require an
  owner/admin session.
- The first slice does not change the
  existing audit retention guarantee from
  `NFR-SEC-008` (≥ 90 days) or the existing
  audit entry shape from `US-026`.
- The bounded migration is forward-safe and
  has a rollback plan. The migration is
  exercised by the verify script so a
  missing column fails the platform check,
  not just the data check.

Tradeoffs:

- The first slice ships only `vi-VN` and
  `en-US`. Adding a third language is an
  explicit follow-up story.
- The first slice ships a minimum-viable
  dictionary. Missing keys fall back to
  `en-US` and emit a
  `locale.missing_key` warning that a future
  story can turn into a CI gate.
- The first slice does not change the
  datetime storage format. The display layer
  uses the resolved timezone; the storage
  layer stays in UTC.
- The first slice does not ship currency,
  number, or measurement localization.
- The first slice does not ship right-to-left
  (RTL) layout support.

## Follow-Up

- Per-tenant locale and per-tenant timezone
  tuning behind the same `I18nService` seam.
- Additional languages (e.g., `ja-JP`,
  `ko-KR`, `zh-CN`) behind the same
  `Locale` enum and dictionary loader.
- A CI gate for missing keys that turns the
  `locale.missing_key` warning into a hard
  build failure.
- Currency, number, and measurement
  localization behind the same
  `I18nService` seam.
- Right-to-left (RTL) layout support
  behind the same `Locale` enum.
- External translation services (DeepL,
  Google Translate, a managed TMS) behind
  the same `I18nService` seam.
- Audit log or analytics export of
  per-user locale and timezone.
- Per-locale A/B test instrumentation
  behind the same `I18nService` seam.
