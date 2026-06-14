# Enforcement boundaries (US-001)

Production auth and domain CRUD are **out of scope** for Foundation. These
boundaries exist so later stories cannot bypass them accidentally.

| Boundary | Code | Rule |
| --- | --- | --- |
| Auth | `src/livelead/boundaries/auth.py` | Every product command/query must authenticate once identity ships. |
| Tenant | `src/livelead/boundaries/tenant.py` | `TenantScope` required for product data reads/writes. |
| RBAC | `src/livelead/boundaries/rbac.py` | Role checks on backend; UI hiding is not sufficient. |
| Audit | `src/livelead/boundaries/audit.py` | Sensitive actions emit `AuditEvent` records, not only logs. |
| Source policy | `src/livelead/boundaries/source_policy.py` | Policy evaluation before connector/browser execution. |

Placeholder domain types (no tables yet): `src/livelead/domain/placeholders.py`
(`Organization`, `User`, `Role`, `TenantScope`, `SourcePolicy`, `AuditEvent`).

Open (not fixed in US-001): exact authentication mechanism, SSO shape — see
`docs/ARCHITECTURE.md` Open Decisions.