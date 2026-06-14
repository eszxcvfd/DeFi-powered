"""event provenance and discovery job linkage

Revision ID: 20260614_0003
Revises: 20260614_0002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0003"
down_revision: Union[str, Sequence[str], None] = "20260614_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("discovery_job_id", sa.String(36), nullable=True))
        batch_op.create_index("ix_events_discovery_job_id", ["discovery_job_id"])
    with op.batch_alter_table("event_source_observations") as batch_op:
        batch_op.add_column(sa.Column("discovery_job_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("content_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("event_source_observations") as batch_op:
        batch_op.drop_column("content_hash")
        batch_op.drop_column("discovery_job_id")
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_index("ix_events_discovery_job_id")
        batch_op.drop_column("discovery_job_id")