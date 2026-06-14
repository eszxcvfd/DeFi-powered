"""Product audit boundary — separate from request logging."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditBoundary:
    """Placeholder: sensitive actions must emit audit records, not only logs."""

    enforced: bool = False
    note: str = "Foundation stub — audit records are product facts per ARCHITECTURE.md."