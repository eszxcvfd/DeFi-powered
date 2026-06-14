"""campaign parent and creation provenance

Revision ID: 20260614_0005
Revises: 20260614_0004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0005"
down_revision: Union[str, Sequence[str], None] = "20260614_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.add_column(sa.Column("parent_campaign_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("created_by_actor", sa.String(128), server_default="analyst"))
        batch_op.add_column(sa.Column("creation_source", sa.String(64), server_default="user"))
        batch_op.add_column(sa.Column("automation_run_id", sa.String(64), nullable=True))
        batch_op.create_index("ix_campaigns_parent_campaign_id", ["parent_campaign_id"])
        batch_op.create_index("ix_campaigns_creation_source", ["creation_source"])


def downgrade() -> None:
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.drop_index("ix_campaigns_creation_source")
        batch_op.drop_index("ix_campaigns_parent_campaign_id")
        batch_op.drop_column("automation_run_id")
        batch_op.drop_column("creation_source")
        batch_op.drop_column("created_by_actor")
        batch_op.drop_column("parent_campaign_id")