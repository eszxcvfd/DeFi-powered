"""scoring suggestion sets and weight snapshots (US-039)

Revision ID: 20260616_0029
Revises: 20260616_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0029"
down_revision: str | Sequence[str] | None = "20260616_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "scoring_suggestion_sets" not in tables:
        op.create_table(
            "scoring_suggestion_sets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("campaign_id", sa.String(36), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
            sa.Column("confidence", sa.Float(), server_default="0"),
            sa.Column("summary", sa.Text(), server_default=""),
            sa.Column("caution_notes_json", sa.Text(), server_default="[]"),
            sa.Column("assumptions_json", sa.Text(), server_default="[]"),
            sa.Column("signals_json", sa.Text(), server_default="[]"),
            sa.Column("deltas_json", sa.Text(), server_default="[]"),
            sa.Column("current_weights_json", sa.Text(), server_default="{}"),
            sa.Column("proposed_weights_json", sa.Text(), server_default="{}"),
            sa.Column("generated_by", sa.String(128), nullable=True),
            sa.Column("decided_by", sa.String(128), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("weight_snapshot_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_scoring_suggestion_sets_campaign",
            "scoring_suggestion_sets",
            ["organization_id", "campaign_id"],
        )
    if "campaign_scoring_weight_snapshots" not in tables:
        op.create_table(
            "campaign_scoring_weight_snapshots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("campaign_id", sa.String(36), nullable=False),
            sa.Column("weights_json", sa.Text(), server_default="{}"),
            sa.Column("source", sa.String(64), nullable=False, server_default="manual"),
            sa.Column("suggestion_set_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_campaign_scoring_weight_snapshots_campaign",
            "campaign_scoring_weight_snapshots",
            ["organization_id", "campaign_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "campaign_scoring_weight_snapshots" in tables:
        op.drop_table("campaign_scoring_weight_snapshots")
    if "scoring_suggestion_sets" in tables:
        op.drop_table("scoring_suggestion_sets")