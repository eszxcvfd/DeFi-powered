"""Bounded browser discovery recipe (pure validation, US-033)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BrowserDiscoveryRecipe:
    start_url: str
    item_selector: str
    title_selector: str | None = None
    link_selector: str | None = None
    description_selector: str | None = None
    wait_for_selector: str | None = None
    max_pages: int = 1
    max_items: int = 50
    time_budget_ms: int = 60_000
    challenge_selectors: tuple[str, ...] = ()


def _coerce_int(value: Any, default: int, *, field: str, errors: list[str], lo: int, hi: int) -> int:
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        errors.append(f"{field}_invalid")
        return default
    if n < lo or n > hi:
        errors.append(f"{field}_out_of_range")
        return default
    return n


def validate_browser_discovery_recipe(data: dict[str, Any]) -> tuple[BrowserDiscoveryRecipe | None, tuple[str, ...]]:
    errors: list[str] = []
    start = (data.get("start_url") or "").strip()
    if not start:
        errors.append("missing_start_url")
    elif not (
        start.startswith("http://")
        or start.startswith("https://")
        or start.startswith("file://")
    ):
        errors.append("invalid_start_url")

    item_sel = (data.get("item_selector") or "").strip()
    if not item_sel:
        errors.append("missing_item_selector")
    elif len(item_sel) > 500:
        errors.append("item_selector_too_long")

    for key in ("title_selector", "link_selector", "description_selector", "wait_for_selector"):
        raw = data.get(key)
        if raw is not None and len(str(raw).strip()) > 500:
            errors.append(f"{key}_too_long")

    max_pages = _coerce_int(data.get("max_pages"), 1, field="max_pages", errors=errors, lo=1, hi=20)
    max_items = _coerce_int(data.get("max_items"), 50, field="max_items", errors=errors, lo=1, hi=200)
    time_budget_ms = _coerce_int(
        data.get("time_budget_ms"), 60_000, field="time_budget_ms", errors=errors, lo=5_000, hi=300_000
    )

    challenge_raw = data.get("challenge_selectors") or []
    challenge: tuple[str, ...] = ()
    if challenge_raw:
        if not isinstance(challenge_raw, list):
            errors.append("challenge_selectors_invalid")
        else:
            challenge = tuple(str(s).strip() for s in challenge_raw if str(s).strip())

    if errors:
        return None, tuple(errors)

    return (
        BrowserDiscoveryRecipe(
            start_url=start,
            item_selector=item_sel,
            title_selector=(data.get("title_selector") or None),
            link_selector=(data.get("link_selector") or None),
            description_selector=(data.get("description_selector") or None),
            wait_for_selector=(data.get("wait_for_selector") or None),
            max_pages=max_pages,
            max_items=max_items,
            time_budget_ms=time_budget_ms,
            challenge_selectors=challenge,
        ),
        (),
    )


def parse_browser_discovery_recipe(rate_limit_json: str | None) -> tuple[BrowserDiscoveryRecipe | None, tuple[str, ...]]:
    if not rate_limit_json:
        return None, ("missing_recipe_config",)
    try:
        root = json.loads(rate_limit_json)
    except json.JSONDecodeError:
        return None, ("invalid_recipe_json",)
    if not isinstance(root, dict):
        return None, ("invalid_recipe_json",)
    nested = root.get("browser_discovery_recipe")
    if isinstance(nested, dict):
        return validate_browser_discovery_recipe(nested)
    if root.get("start_url") and root.get("item_selector"):
        return validate_browser_discovery_recipe(root)
    return None, ("missing_recipe_config",)