"""Named domain concepts — no persistence, no framework imports (design.md)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RoleName(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    SALES = "sales"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


@dataclass(frozen=True, slots=True)
class Organization:
    id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    organization_id: UUID
    email: str


@dataclass(frozen=True, slots=True)
class Role:
    name: RoleName


@dataclass(frozen=True, slots=True)
class TenantScope:
    organization_id: UUID


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    """Evaluated before connector execution — enforcement in later stories."""

    connector_allowed: bool = False


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Product audit fact — separate from request logs."""

    action: str
    actor_user_id: UUID | None = None