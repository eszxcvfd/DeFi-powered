"""Health and smoke response models."""

from pydantic import BaseModel, Field


class RuntimeComponentStatus(BaseModel):
    name: str
    status: str = Field(description="ok | degraded | unavailable")
    detail: str | None = None


class HealthStatus(BaseModel):
    service: str = "livelead-api"
    version: str
    environment: str
    status: str = "ok"
    components: list[RuntimeComponentStatus] = Field(default_factory=list)
