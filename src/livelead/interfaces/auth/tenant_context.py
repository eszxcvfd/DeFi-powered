"""Tenant scope at HTTP boundary — Foundation dev header until real auth."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException

# Seeded in migration for local/dev flows (US-002).
DEV_ORGANIZATION_ID = UUID("00000000-0000-4000-8000-000000000001")


@dataclass(frozen=True, slots=True)
class TenantContext:
    organization_id: UUID
    actor_role: str = "analyst"


async def get_tenant_context(
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_actor_role: str | None = Header(default="analyst", alias="X-Actor-Role"),
) -> TenantContext:
    if x_organization_id:
        try:
            org_id = UUID(x_organization_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid X-Organization-Id") from exc
    else:
        org_id = DEV_ORGANIZATION_ID
    return TenantContext(organization_id=org_id, actor_role=x_actor_role or "analyst")


def require_scoring_editor(ctx: TenantContext) -> None:
    if ctx.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot edit scoring weights")
