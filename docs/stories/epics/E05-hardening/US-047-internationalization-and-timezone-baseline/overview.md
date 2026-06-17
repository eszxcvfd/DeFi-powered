# Overview

## Current Behavior

`US-001` through `US-046` delivered a broad MVP and
the first bounded hardening slices for LiveLead.
The product now has:

- A modular monolith with a Python API, a worker,
  a scheduler, a browser worker, a SQLite store,
  a Redis broker, and a React/TypeScript UI.
- A bounded audit log (`US-026`), a bounded
  identity and access baseline (`US-027`), a
  bounded member management baseline (`US-028`),
  a bounded notification delivery baseline
  (`US-029`), a bounded real-environment cutover
  (`US-040`), a bounded operational observability
  baseline (`US-041`), a bounded external metrics
  pipeline baseline (`US-042`), a bounded backup
  and restore operations baseline (`US-043`), a
  bounded performance baseline (`US-044`), a
  bounded event calendar export slice (`US-045`),
  and a bounded connector health surface slice
  (`US-046`).

`SPEC.md` section 10.7 (`NFR-I18N-001`,
`NFR-I18N-002`, `NFR-I18N-003`) commits the
product to:

> **NFR-I18N-001** — UI phải tách chuỗi khỏi code
> và hỗ trợ ít nhất `vi-VN` và `en-US`.
>
> **NFR-I18N-002** — Hệ thống phải lưu datetime UTC
> và hiển thị theo timezone người dùng.
>
> **NFR-I18N-003** — Search phải hỗ trợ Unicode,
> dấu tiếng Việt và normalization.

The product still has no bounded i18n and
timezone baseline:

- There is no closed `Locale` enum. Every
  translation request has to infer the supported
  set from a code comment, a README, or a memory
  of how the API was written.
- There is no bounded `Timezone` validation.
  The product does not even know which timezone a
  user is in, and the audit log cannot show the
  previous-vs-new timezone when a user switches.
- There is no `users.locale` column. The default
  locale is whatever the browser sends, which is
  not stable across sessions and not enforceable.
- There is no `users.timezone` column. The
  `<LocalizedDatetime>` component does not exist;
  every date or time is rendered with
  `new Date(...).toLocaleString()` and produces
  inconsistent results across regions.
- The first slice does not exist for `vi-VN` or
  `en-US`. Vietnamese strings are not even
  available; English strings are baked into the
  React source.
- The audit log from `US-026` cannot record a
  locale or timezone change because there is no
  closed `Locale` enum, no bounded `Timezone`
  validation, and no `I18nService` to read from.

`SPEC.md` section 17 lists internationalization
as part of the production readiness review in
"Giai đoạn 5 — Hardening". The product cannot
reach that milestone without a bounded i18n and
timezone baseline.

The next step in the hardening epic is therefore
a bounded i18n and timezone slice that turns
`NFR-I18N-001`, `NFR-I18N-002`, and `NFR-I18N-003`
into a documented contract, a closed `Locale`
enum, a bounded `Timezone` validation, a
per-user and per-organization locale/timezone
surface, a reusable React hook and component, a
minimum-viable dictionary, and a bounded
verification command that a future story can
extend without re-opening the audit or the
authentication boundary.

## Target Behavior

This story establishes the first bounded i18n
and timezone baseline for LiveLead. After the
story is complete:

- A new durable `users.locale` column and a
  new durable `users.timezone` column exist
  on the existing `users` table, with bounded
  migration validation.
- A new durable `organizations.default_locale`
  column and a new durable
  `organizations.default_timezone` column
  exist on the existing `organizations` table,
  with the same bounded migration validation.
- A new closed `Locale` enum (`vi-VN`, `en-US`)
  that the bounded surfaces read from and
  that the API and UI reject with
  `LOCALE_UNSUPPORTED` for any value outside
  the closed set.
- A new bounded `Timezone` value type that is
  validated against the IANA tz database and
  that the API and UI reject with
  `TIMEZONE_INVALID` for any value outside
  the supported set.
- A new `I18nService` exposes the bounded
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
- A new owner/admin-only REST surface for the
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
- A new product doc
  (`docs/product/internationalization-and-timezone.md`)
  that documents the closed `Locale` enum, the
  bounded `Timezone` validation, the per-user
  default fallback order, the datetime storage
  rule, the audit entry shape, the API surface,
  the UI surface, and the
  `locale.unsupported.rejected` rejection
  contract.
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
  and platform checks defined in `validation.md`
  and is wired into `harness-cli story verify`
  and `harness-cli story verify-all`.

The slice stops at the local-first, single-host
baseline. Distributed translation services,
per-tenant locale, RTL layout, currency/number
localization, and right-to-left (RTL) support
remain in the follow-up backlog.

## Affected Users

- Vietnamese-speaking analysts, sales/BD users,
  reviewers, and admins who need the product to
  render Vietnamese strings and Vietnam timezone
  consistently.
- English-speaking analysts, sales/BD users,
  reviewers, and admins who need a stable
  `en-US` locale and a stable timezone across
  sessions.
- Owners/Admins responsible for the
  real-environment pilot. They need a per-organization
  default locale and timezone so the same
  product behaves the same way for every user
  in the workspace.
- Performance and SRE engineers who need a
  documented i18n and timezone baseline and a
  bounded `I18nService` they can extend for
  future languages.
- Future implementation agents and engineers
  extending the `Locale` enum, the
  `I18nService`, the dictionary loader, or the
  audit entry shape that need a stable
  internationalization and timezone contract.

## Affected Product Docs

- `docs/product/identity-and-access.md`
  (`US-027` contract; this story extends the
  user payload with `locale` and `timezone`,
  it does not redefine the authentication
  boundary, the RBAC roles, or the tenant
  isolation contract).
- `docs/product/member-management-and-access-governance.md`
  (`US-028` contract; this story extends the
  organization payload with
  `default_locale` and `default_timezone`,
  it does not redefine the member
  governance contract).
- `docs/product/notification-delivery-and-preferences.md`
  (`US-029` contract; this story consumes the
  resolved locale and timezone for the
  notification payload, it does not redefine
  the in-app or email delivery contract).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract; the locale and timezone
  changes emit
  `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected` audit
  entries with the same secret-safe payload
  contract).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract; the locale and timezone
  updates are covered by the same
  `EnvironmentMode` bound and launch-gate
  seam).
- `docs/product/internationalization-and-timezone.md` (new
  product doc that this story seeds as the
  living contract for the internationalization
  and timezone domain).

## Non-Goals

- Translating every UI string in the product.
  The first slice ships a minimum-viable
  dictionary; a future story can add
  additional languages, additional keys, and
  CI gates for missing keys.
- Datetime storage format changes. The first
  slice keeps the existing UTC storage
  contract; only the display layer changes.
- Per-tenant locale or per-tenant timezone
  beyond the organization default. The first
  slice ships one `default_locale` and one
  `default_timezone` per organization; a
  future story can extend the surface with
  per-tenant tuning without redefining the
  contract.
- Right-to-left (RTL) layout support. The
  first slice ships `vi-VN` (LTR) and `en-US`
  (LTR); RTL is an explicit follow-on
  story.
- External translation services (DeepL,
  Google Translate, a managed TMS).
- Currency, number, or measurement
  localization. The first slice ships
  locale-aware datetime formatting only;
  currency, number, and measurement
  formatting are explicit follow-on
  stories.
- Audit log or analytics export of per-user
  locale and timezone. The first slice
  records the change through the audit
  entry shape from `US-026`; a future story
  can extend the export surface.
- Replacing the existing audit log from
  `US-026`. This story extends the audit
  entry shape with
  `user.locale.updated`,
  `organization.locale.updated`, and
  `locale.unsupported.rejected`; it does
  not redefine the `AuditEntryRow` or the
  audit retention guarantee.
- Replacing the existing identity and access
  baseline from `US-027`. This story
  extends the user payload with `locale`
  and `timezone`; it does not redefine
  the authentication boundary, the RBAC
  roles, or the tenant isolation contract.
- Replacing the existing member management
  baseline from `US-028`. This story
  extends the organization payload with
  `default_locale` and `default_timezone`;
  it does not redefine the member
  governance contract.
