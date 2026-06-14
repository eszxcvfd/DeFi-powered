"""content handoff records and draft usage status

Revision ID: 20260614_0009
Revises: 20260614_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0009"
down_revision: str | Sequence[str] | None = "20260614_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "generated_content_drafts" in tables:
        cols = {c["name"] for c in insp.get_columns("generated_content_drafts")}
        if "usage_status" not in cols:
            op.add_column(
                "generated_content_drafts",
                sa.Column("usage_status", sa.String(32), server_default="not_used", nullable=False),
            )
    if "content_handoff_records" not in tables:
        op.create_table(
            "content_handoff_records",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("draft_id", sa.String(36), nullable=False, index=True),
            sa.Column("event_id", sa.String(36), nullable=False, index=True),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("export_format", sa.String(32), server_default=""),
            sa.Column("body_revision", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("content_handoff_records")
    op.drop_column("generated_content_drafts", "usage_status")
