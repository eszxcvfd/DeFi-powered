"""Tenant scope boundary — mandatory for product data access in later stories."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantBoundary:
    """Placeholder: tenant_id must accompany every command/query touching product data."""

    enforced: bool = False
    note: str = "Foundation stub — tenant scope required before persisted domain CRUD."
