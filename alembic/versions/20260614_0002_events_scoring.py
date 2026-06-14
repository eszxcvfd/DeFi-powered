"""events and event_scores

Revision ID: 20260614_0002
Revises: 20260613_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0002"
down_revision: str | Sequence[str] | None = "20260613_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(36), nullable=False, index=True),
        sa.Column("canonical_title", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("organizer", sa.String(300), server_default=""),
        sa.Column("region", sa.String(120), server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "event_source_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False, index=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_title", sa.String(500), server_default=""),
        sa.Column("external_id", sa.String(200), nullable=True),
    )
    op.create_table(
        "event_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(36), nullable=False, index=True),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("priority_level", sa.String(32), nullable=False),
        sa.Column("scoring_version", sa.String(64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weights_snapshot_json", sa.Text(), server_default="{}"),
        sa.Column("components_json", sa.Text(), server_default="[]"),
        sa.Column("explanation_json", sa.Text(), server_default="{}"),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("event_scores")
    op.drop_table("event_source_observations")
    op.drop_table("events")
