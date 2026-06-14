from datetime import UTC, datetime
from uuid import UUID, uuid4

from livelead.application.campaigns.list_tree import build_campaign_forest, flatten_forest
from livelead.domain.campaigns.models import (
    Campaign,
    CampaignStatus,
    DateRange,
    IcpCriteria,
    ScoringWeights,
)


def _c(name: str, parent: UUID | None = None, source: str = "user") -> Campaign:
    now = datetime.now(UTC)
    pid = parent
    return Campaign(
        id=uuid4(),
        organization_id=uuid4(),
        name=name,
        description="",
        target_industry="T",
        product_or_service_focus="",
        market_regions=(),
        languages=(),
        timezone="UTC",
        date_range=DateRange(),
        positive_keywords=(),
        exclude_keywords=(),
        icp=IcpCriteria(),
        scoring_weights=ScoringWeights(),
        status=CampaignStatus.DRAFT,
        parent_campaign_id=pid,
        created_by_actor="test",
        creation_source=source,
        automation_run_id=None,
        created_at=now,
        updated_at=now,
    )


def test_forest_parent_before_children():
    root = _c("Parent", None, "automation_root")
    child = _c("Child", root.id, "playwright")
    forest = build_campaign_forest([child, root])
    flat = flatten_forest(forest)
    assert flat[0].campaign.name == "Parent"
    assert flat[1].depth == 1
    assert flat[1].parent_name == "Parent"