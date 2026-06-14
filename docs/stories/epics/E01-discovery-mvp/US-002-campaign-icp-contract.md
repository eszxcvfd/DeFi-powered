# US-002 Campaign ICP Contract

## Status

implemented

## Lane

normal

## Product Contract

LiveLead must let an analyst create and update a campaign with explicit market
intent, ICP criteria, and scoring-weight settings before any discovery work
starts, using a minimal UI/API contract that leaves source selection and
run-discovery behavior visibly deferred.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/campaign-and-icp.md`
- `docs/product/platform-and-automation-policy.md`

## Acceptance Criteria

- Users can create and update a campaign with name, description, target
  industry, product or service focus, market regions, languages, timezone, date
  range, positive keywords, and exclude keywords.
- Users can create and update ICP criteria covering industry, organization
  type, company size, role or title targets, country or region, pain points,
  use cases, positive keywords, and excluded keywords.
- The minimum API surface exists for list/create/detail/update via
  `GET/POST /campaigns` and `GET/PATCH /campaigns/{id}`, with organization
  scoping and stable request or response contracts.
- The UI exposes a minimal campaign list plus a wizard aligned with `UI-002`,
  where source selection is clearly deferred to `US-003` and run-discovery is
  clearly deferred to `US-004`.
- Users with the allowed role can edit scoring weights for a campaign and see
  those settings persist in campaign detail, even though scoring execution and
  re-score behavior remain out of scope.

## Design Notes

- Commands: create campaign, update campaign, save ICP criteria, save scoring
  weights.
- Queries: list campaigns, get campaign detail.
- API: `GET/POST /campaigns`, `GET/PATCH /campaigns/{id}`.
- Tables: extend campaign persistence for target intent, keyword criteria,
  `icp_json`, and `scoring_weights_json`; do not add source-assignment or
  discovery-job coupling in this story.
- Domain rules: organization-scoped records, no source required for draft save,
  and deferred discovery effects when criteria change.
- UI surfaces: campaign index, campaign wizard, disabled source step, disabled
  run-discovery action, editable scoring-weight step.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Request validation and ICP/scoring-weight mapping tests. |
| Integration | API + persistence tests for create/list/detail/update and organization scoping. |
| E2E | Browser flow that creates a campaign in the wizard and reopens it from the list/detail surface. |
| Platform | Story verify command updates Harness matrix and keeps frontend/backend checks runnable. |
| Release | Not required for this story beyond standard local proof. |

## Harness Delta

- Added `docs/product/campaign-and-icp.md` so the story has a domain-specific
  product contract instead of relying only on `SPEC.md`.
- Marked `E01 Discovery MVP` as active in the backlog now that its first story
  packet exists.

## Evidence

- `./scripts/verify-us-002.sh` (extends foundation verify): pytest campaign API + validation, Playwright wizard e2e.
- API: `GET/POST /campaigns`, `GET/PATCH /campaigns/{id}` with `X-Organization-Id` scoping.
- UI: campaign list, UI-002 wizard (sources US-003, discovery US-004 deferred).
