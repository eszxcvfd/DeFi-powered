"""audience hypotheses

Revision ID: 20260614_0004
Revises: 20260614_0003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0004"
down_revision: Union[str, Sequence[str], None] = "20260614_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audience_hypotheses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False, index=True),
        sa.Column("segment_name", sa.String(300), nullable=False),
        sa.Column("fit_type", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.Text(), server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("generated_by", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audience_hypotheses")