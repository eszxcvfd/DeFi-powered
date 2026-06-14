import json
from datetime import datetime
from uuid import UUID

from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
    SourceGovernance,
    SourcePolicy,
)
from livelead.infrastructure.db.models import SourceRow


def _policy_from_json(raw: str) -> SourcePolicy:
    data = json.loads(raw or "{}")
    return SourcePolicy(
        access_mode=AccessMode(data.get("access_mode", "api")),
        quota_per_day=int(data.get("quota_per_day", 1000)),
        quota_used_today=int(data.get("quota_used_today", 0)),
        window_start_hour=int(data.get("window_start_hour", 0)),
        window_end_hour=int(data.get("window_end_hour", 23)),
        retention_days=int(data.get("retention_days", 90)),
        valid=bool(data.get("valid", True)),
    )


def policy_to_json(policy: SourcePolicy) -> str:
    return json.dumps(
        {
            "access_mode": policy.access_mode.value,
            "quota_per_day": policy.quota_per_day,
            "quota_used_today": policy.quota_used_today,
            "window_start_hour": policy.window_start_hour,
            "window_end_hour": policy.window_end_hour,
            "retention_days": policy.retention_days,
            "valid": policy.valid,
        }
    )


def row_to_source(row: SourceRow) -> SourceGovernance:
    return SourceGovernance(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        name=row.name,
        domain=row.domain,
        connector_type=ConnectorType(row.connector_type),
        automation_engine=row.automation_engine or "none",
        authentication_mode=AuthenticationMode(row.authentication_mode),
        enabled=bool(row.enabled),
        approved=bool(row.approved),
        approved_at=row.approved_at,
        approved_by=row.approved_by,
        policy=_policy_from_json(row.policy_json),
        has_secret=bool(row.secret_ciphertext),
        created_at=row.created_at if isinstance(row.created_at, datetime) else datetime.now(),
        updated_at=row.updated_at if isinstance(row.updated_at, datetime) else datetime.now(),
    )
