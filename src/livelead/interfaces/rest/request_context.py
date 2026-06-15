"""HTTP request context capture for audit (US-026)."""

from __future__ import annotations

from starlette.requests import Request

from livelead.application.audit.audit_service import make_context
from livelead.domain.audit.model import AuditContext


def capture_request_context(request: Request, *, workflow: str = "") -> AuditContext:
    """Build an AuditContext from a Starlette request.

    Reads the request id assigned by the request logging middleware
    (RequestLoggingMiddleware) and a few optional correlation headers.
    """

    state = getattr(request, "state", None)
    request_id = ""
    if state is not None:
        request_id = getattr(state, "request_id", "") or ""
    headers = request.headers
    correlation_id = (
        headers.get("x-correlation-id")
        or headers.get("x-trace-id")
        or ""
    )
    session_id = headers.get("x-session-id") or ""
    ip = (
        headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "")
        or ""
    )
    user_agent = headers.get("user-agent") or ""

    return make_context(
        request_id=request_id,
        session_id=session_id,
        correlation_id=correlation_id,
        ip=ip,
        user_agent=user_agent,
        workflow=workflow,
    )
