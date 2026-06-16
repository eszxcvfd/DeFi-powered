import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.identity import can_access_admin_connector
from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    SourcePolicy,
)
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source
from livelead.infrastructure.secrets.vault import SecretVault, redact_secret
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.policy")

router = APIRouter(prefix="/admin/connectors", tags=["admin-connectors"])


def require_admin(ctx: TenantContext) -> None:
    if not can_access_admin_connector(ctx.role):
        raise HTTPException(status_code=403, detail="admin role required")


def vault_for(request: Request) -> SecretVault:
    return SecretVault(request.app.state.settings.secret_master_key)


class PolicySchema(BaseModel):
    access_mode: str = "api"
    quota_per_day: int = 1000
    quota_used_today: int = 0
    window_start_hour: int = 0
    window_end_hour: int = 23
    retention_days: int = 90
    valid: bool = True


class ConnectorCreateSchema(BaseModel):
    name: str
    domain: str
    connector_type: str
    automation_engine: str = "none"
    authentication_mode: str = "none"
    enabled: bool = True
    approved: bool = False
    policy: PolicySchema = Field(default_factory=PolicySchema)
    secret_plaintext: str | None = None


class ConnectorPatchSchema(BaseModel):
    name: str | None = None
    domain: str | None = None
    connector_type: str | None = None
    automation_engine: str | None = None
    enabled: bool | None = None
    approved: bool | None = None
    policy: PolicySchema | None = None
    secret_plaintext: str | None = None
    rate_limit_json: dict | None = None


class ConnectorViewSchema(BaseModel):
    id: UUID
    name: str
    domain: str
    connector_type: str
    automation_engine: str
    authentication_mode: str
    enabled: bool
    approved: bool
    approved_by: str | None
    policy_state: str
    runnable: bool
    denied_reasons: list[str]
    has_secret: bool
    secret_display: str
    preferred_over_browser: bool


def _policy_from_schema(s: PolicySchema) -> SourcePolicy:
    return SourcePolicy(
        access_mode=AccessMode(s.access_mode),
        quota_per_day=s.quota_per_day,
        quota_used_today=s.quota_used_today,
        window_start_hour=s.window_start_hour,
        window_end_hour=s.window_end_hour,
        retention_days=s.retention_days,
        valid=s.valid,
    )


def _to_view(source, decision) -> ConnectorViewSchema:
    state = "runnable" if decision.runnable else "denied"
    if not source.enabled:
        state = "disabled"
    elif not source.approved:
        state = "pending_approval"
    return ConnectorViewSchema(
        id=source.id,
        name=source.name,
        domain=source.domain,
        connector_type=source.connector_type.value,
        automation_engine=source.automation_engine,
        authentication_mode=source.authentication_mode.value,
        enabled=source.enabled,
        approved=source.approved,
        approved_by=source.approved_by,
        policy_state=state,
        runnable=decision.runnable,
        denied_reasons=list(decision.reasons),
        has_secret=source.has_secret,
        secret_display=redact_secret("present") if source.has_secret else "",
        preferred_over_browser=decision.preferred_over_browser,
    )


@router.get("", response_model=list[ConnectorViewSchema])
async def list_connectors(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    repo = SourceRepository(session)
    sources = await repo.list_for_organization(tenant.organization_id)
    views = []
    for s in sources:
        d = evaluate_source_policy(s)
        if not d.runnable:
            logger.info(
                "policy_denied source_id=%s reasons=%s %s",
                s.id,
                d.reasons,
                vault_for(request).safe_log_fields(has_secret=s.has_secret),
            )
        views.append(_to_view(s, d))
    await session.commit()
    return views


@router.post("", response_model=ConnectorViewSchema, status_code=201)
async def create_connector(
    body: ConnectorCreateSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    try:
        ConnectorType(body.connector_type)
        AuthenticationMode(body.authentication_mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    vault = vault_for(request)
    ciphertext = vault.encrypt(body.secret_plaintext) if body.secret_plaintext else None
    repo = SourceRepository(session)
    row = SourceRepository.new_row(
        tenant.organization_id,
        {
            "name": body.name,
            "domain": body.domain,
            "connector_type": body.connector_type,
            "automation_engine": body.automation_engine,
            "authentication_mode": body.authentication_mode,
            "enabled": body.enabled,
            "approved": body.approved,
            "approved_by": tenant.actor_role if body.approved else None,
            "approved_at": datetime.now(UTC) if body.approved else None,
            "policy": _policy_from_schema(body.policy),
            "secret_ciphertext": ciphertext,
        },
    )
    source = await repo.add(row)
    await session.commit()
    d = evaluate_source_policy(source)
    return _to_view(source, d)


@router.patch("/{connector_id}", response_model=ConnectorViewSchema)
async def patch_connector(
    connector_id: UUID,
    body: ConnectorPatchSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    repo = SourceRepository(session)
    row = await repo.get(connector_id, tenant.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="connector not found")
    patch: dict = body.model_dump(exclude_unset=True)
    if body.policy is not None:
        patch["policy"] = _policy_from_schema(body.policy)
    if body.secret_plaintext:
        patch["secret_ciphertext"] = vault_for(request).encrypt(body.secret_plaintext)
        patch.pop("secret_plaintext", None)
    if body.approved is True:
        patch["approved_by"] = tenant.actor_role
        patch["approved_at"] = datetime.now(UTC)
    if body.rate_limit_json is not None:
        import json as _json

        patch["rate_limit_json"] = _json.dumps(body.rate_limit_json)
    source = await repo.apply_patch(row, patch)
    await session.commit()
    d = evaluate_source_policy(source)
    if not d.runnable:
        logger.info("policy_denied source_id=%s reasons=%s", source.id, d.reasons)
    return _to_view(source, d)


@router.get("/{connector_id}", response_model=ConnectorViewSchema)
async def get_connector(
    connector_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    repo = SourceRepository(session)
    row = await repo.get(connector_id, tenant.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="connector not found")
    source = row_to_source(row)
    d = evaluate_source_policy(source)
    return _to_view(source, d)
