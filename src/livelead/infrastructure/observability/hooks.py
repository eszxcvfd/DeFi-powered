"""Register tracing/error hooks when env enables them (Foundation: no-op)."""

import logging
import os

logger = logging.getLogger("livelead.observability")


def register_observability_hooks(app) -> None:
    """Call from API composition root. OTel/Sentry activate when configured."""
    if os.getenv("LIVELEAD_OTEL_ENABLED", "").lower() in ("1", "true", "yes"):
        logger.info("OpenTelemetry hook point reserved (not wired in Foundation)")
    if os.getenv("LIVELEAD_SENTRY_DSN"):
        logger.info("Sentry hook point reserved (not wired in Foundation)")
    _ = app
