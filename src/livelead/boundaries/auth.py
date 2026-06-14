"""Authentication boundary — production flows deferred; must not be bypassed later."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthBoundary:
    """Placeholder: all product commands/queries must pass through auth once implemented."""

    enforced: bool = False
    note: str = "Foundation stub — enforce in identity stories before domain mutations."
