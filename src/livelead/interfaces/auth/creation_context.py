"""Who created a campaign and from which surface."""

from dataclasses import dataclass

from fastapi import Header, Request


@dataclass(frozen=True, slots=True)
class CreationContext:
    created_by_actor: str
    creation_source: str
    automation_run_id: str | None = None


async def get_creation_context(
    request: Request,
    x_actor_role: str | None = Header(default="analyst", alias="X-Actor-Role"),
    x_actor_label: str | None = Header(default=None, alias="X-Actor-Label"),
    x_creation_source: str | None = Header(default=None, alias="X-Creation-Source"),
    x_automation_run_id: str | None = Header(default=None, alias="X-Automation-Run-Id"),
) -> CreationContext:
    source = (x_creation_source or "user").strip().lower()[:64]
    ua = (request.headers.get("user-agent") or "").lower()
    if source == "user" and "playwright" in ua:
        source = "playwright"
    actor = (x_actor_label or x_actor_role or "analyst").strip()[:128]
    if source == "playwright" and actor == "analyst":
        actor = "e2e-runner"
    run_id = (x_automation_run_id or "").strip()[:64] or None
    return CreationContext(
        created_by_actor=actor,
        creation_source=source,
        automation_run_id=run_id,
    )