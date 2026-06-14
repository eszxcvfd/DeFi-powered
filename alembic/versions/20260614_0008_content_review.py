"""content review decisions and draft revision fields

Revision ID: 20260614_0008
Revises: 20260614_0007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0008"
down_revision: Union[str, Sequence[str], None] = "20260614_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "generated_content_drafts" in tables:
        cols = {c["name"] for c in insp.get_columns("generated_content_drafts")}
        if "body_revision" not in cols:
            op.add_column("generated_content_drafts", sa.Column("body_revision", sa.Integer(), server_default="1"))
        if "reviewer_assignee" not in cols:
            op.add_column("generated_content_drafts", sa.Column("reviewer_assignee", sa.String(128), server_default=""))
    if "content_review_decisions" not in tables:
        op.create_table(
            "content_review_decisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("draft_id", sa.String(36), nullable=False, index=True),
            sa.Column("event_id", sa.String(36), nullable=False, index=True),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("from_status", sa.String(32), nullable=False),
            sa.Column("to_status", sa.String(32), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("note", sa.Text(), server_default=""),
            sa.Column("body_revision", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("content_review_decisions")
    op.drop_column("generated_content_drafts", "reviewer_assignee")
    op.drop_column("generated_content_drafts", "body_revision")