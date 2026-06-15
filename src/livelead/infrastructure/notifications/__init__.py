"""Notifications infrastructure — US-029."""

from .email_provider import (
    EmailRequest,
    EmailResult,
    InMemoryEmailProvider,
    NotificationProviderAdapter,
    default_email_provider,
)

__all__ = [
    "EmailRequest",
    "EmailResult",
    "InMemoryEmailProvider",
    "NotificationProviderAdapter",
    "default_email_provider",
]
