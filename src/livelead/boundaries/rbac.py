"""RBAC boundary — roles gate commands/queries in later stories."""

from dataclasses import dataclass

from livelead.domain.placeholders import RoleName


@dataclass(frozen=True, slots=True)
class RbacBoundary:
    """Placeholder: backend must enforce role permissions, not UI-only hiding."""

    enforced: bool = False
    note: str = "Foundation stub — RBAC on every product command/query per ARCHITECTURE.md."

    def allows(self, role: RoleName, action: str) -> bool:
        """Foundation: deny all mutations; allow read-only smoke actions only in tests."""
        _ = (role, action)
        return False
