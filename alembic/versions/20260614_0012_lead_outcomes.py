"""lead outcome fields on activity timeline

Revision ID: 20260614_0012
Revises: 20260614_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0012"
down_revision: str | Sequence[str] | None = "20260614_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("lead_activities")}
    if "outcome_type" not in cols:
        op.add_column(
            "lead_activities", sa.Column("outcome_type", sa.String(32), server_default="")
        )
    if "occurred_at" not in cols:
        op.add_column(
            "lead_activities", sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True)
        )
    if "linked_content_draft_id" not in cols:
        op.add_column(
            "lead_activities",
            sa.Column("linked_content_draft_id", sa.String(36), server_default=""),
        )


def downgrade() -> None:
    op.drop_column("lead_activities", "linked_content_draft_id")
    op.drop_column("lead_activities", "occurred_at")
    op.drop_column("lead_activities", "outcome_type")
