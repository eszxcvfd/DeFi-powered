"""Source policy boundary — checked before connector execution."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourcePolicyBoundary:
    """Placeholder: connectors must not run without policy evaluation."""

    enforced: bool = True
    note: str = "US-003/004 — policy before run; mock discovery worker enforces at job start."