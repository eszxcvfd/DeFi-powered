"""Build hierarchical campaign list for API/UI."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from livelead.domain.campaigns.lineage import display_source_label
from livelead.domain.campaigns.models import Campaign


@dataclass(frozen=True, slots=True)
class CampaignListNode:
    campaign: Campaign
    parent_campaign_id: UUID | None
    parent_name: str | None
    created_by_actor: str
    creation_source: str
    creation_source_label: str
    automation_run_id: str | None
    child_count: int
    depth: int
    children: tuple[CampaignListNode, ...]


def build_campaign_forest(campaigns: list[Campaign]) -> list[CampaignListNode]:
    by_id = {c.id: c for c in campaigns}
    children_map: dict[UUID | None, list[Campaign]] = {}
    for c in campaigns:
        pid = c.parent_campaign_id if c.parent_campaign_id in by_id else None
        children_map.setdefault(pid, []).append(c)

    def sort_key(c: Campaign) -> tuple:
        return (0 if c.creation_source == "automation_root" else 1, c.name.lower())

    for key in children_map:
        children_map[key].sort(key=sort_key)

    def node_for(c: Campaign, depth: int) -> CampaignListNode:
        kids = children_map.get(c.id, [])
        child_nodes = tuple(node_for(ch, depth + 1) for ch in kids)
        parent_name = by_id[c.parent_campaign_id].name if c.parent_campaign_id and c.parent_campaign_id in by_id else None
        return CampaignListNode(
            campaign=c,
            parent_campaign_id=c.parent_campaign_id,
            parent_name=parent_name,
            created_by_actor=c.created_by_actor,
            creation_source=c.creation_source,
            creation_source_label=display_source_label(c.creation_source),
            automation_run_id=c.automation_run_id,
            child_count=len(kids),
            depth=depth,
            children=child_nodes,
        )

    roots = children_map.get(None, [])
    return [node_for(r, 0) for r in roots]


def flatten_forest(forest: list[CampaignListNode]) -> list[CampaignListNode]:
    out: list[CampaignListNode] = []

    def walk(n: CampaignListNode) -> None:
        out.append(n)
        for ch in n.children:
            walk(ch)

    for root in forest:
        walk(root)
    return out