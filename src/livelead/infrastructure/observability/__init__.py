"""OpenTelemetry and Sentry hook points — external wiring deferred."""

from livelead.infrastructure.observability.hooks import register_observability_hooks

__all__ = ["register_observability_hooks"]