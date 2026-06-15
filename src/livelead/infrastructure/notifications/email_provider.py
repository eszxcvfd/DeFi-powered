"""Email provider adapter boundary (US-029).

The first slice ships an in-memory implementation. A future SMTP or
transactional-email provider (SES, Postmark, Resend) implements the
same Protocol without changing the notification service.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("livelead.notifications.email")


@dataclass(frozen=True, slots=True)
class EmailRequest:
    recipient: str
    subject: str
    body: str
    notification_id: str
    notification_type: str
    deep_link: str = ""


@dataclass(frozen=True, slots=True)
class EmailResult:
    success: bool
    provider_message_id: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


class NotificationProviderAdapter(Protocol):
    """Adapter contract for the email provider used by US-029."""

    name: str

    async def send(self, request: EmailRequest) -> EmailResult:  # pragma: no cover - protocol
        ...


class InMemoryEmailProvider:
    """In-memory email provider used by tests and the local dev stack.

    Each call to `send` records the request so the verification
    scripts can assert exactly which emails were attempted. A
    configurable failure mode lets tests exercise the delivery-failed
    audit path deterministically.
    """

    name = "in_memory"

    def __init__(self, *, fail_recipients: set[str] | None = None) -> None:
        self._sent: list[EmailRequest] = []
        self._fail = set(r.strip().lower() for r in (fail_recipients or set()))

    @property
    def sent(self) -> list[EmailRequest]:
        return list(self._sent)

    def configure_failure(self, recipient: str, enabled: bool = True) -> None:
        normalized = recipient.strip().lower()
        if enabled:
            self._fail.add(normalized)
        else:
            self._fail.discard(normalized)

    async def send(self, request: EmailRequest) -> EmailResult:
        recipient = (request.recipient or "").strip().lower()
        self._sent.append(request)
        if not recipient:
            return EmailResult(
                success=False,
                provider_message_id="",
                diagnostics={"reason": "missing_recipient"},
            )
        if recipient in self._fail:
            logger.info("email_provider_simulated_failure recipient=%s", recipient)
            return EmailResult(
                success=False,
                provider_message_id="",
                diagnostics={"reason": "simulated_failure"},
            )
        return EmailResult(
            success=True,
            provider_message_id=secrets.token_urlsafe(12),
            diagnostics={"bytes": len(request.body or "")},
        )


def default_email_provider() -> NotificationProviderAdapter:
    """Return the in-memory provider for the local dev and test stack."""

    return InMemoryEmailProvider()


__all__ = [
    "EmailRequest",
    "EmailResult",
    "InMemoryEmailProvider",
    "NotificationProviderAdapter",
    "default_email_provider",
]
