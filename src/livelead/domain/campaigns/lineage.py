"""Campaign parent/child and automation provenance."""

from enum import StrEnum

E2E_ROOT_NAME = "E2E Automation (parent)"
E2E_ROOT_SOURCE = "automation_root"


class CreationSource(StrEnum):
    USER = "user"
    PLAYWRIGHT = "playwright"
    API = "api"
    HARNESS = "harness"
    AUTOMATION_ROOT = "automation_root"


def display_source_label(source: str) -> str:
    labels = {
        CreationSource.USER.value: "Manual",
        CreationSource.PLAYWRIGHT.value: "E2E test",
        CreationSource.API.value: "API",
        CreationSource.HARNESS.value: "Harness",
        CreationSource.AUTOMATION_ROOT.value: "Automation parent",
    }
    return labels.get(source, source)