"""notification tables (US-029)

Revision ID: 20260615_0022
Revises: 20260615_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260615_0022"
down_revision: str | Sequence[str] | None = "20260615_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "user_notifications" not in tables:
        op.create_table(
            "user_notifications",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("notification_type", sa.String(64), nullable=False),
            sa.Column("state", sa.String(32), nullable=False, server_default="unread"),
            sa.Column("source_record_type", sa.String(64), nullable=False),
            sa.Column("source_record_id", sa.String(96), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("deep_link", sa.String(1024), nullable=False, server_default=""),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
        op.create_index(
            "ix_user_notifications_organization_id", "user_notifications", ["organization_id"]
        )
        op.create_index(
            "ix_user_notifications_notification_type", "user_notifications", ["notification_type"]
        )
        op.create_index("ix_user_notifications_state", "user_notifications", ["state"])
        op.create_index(
            "ix_user_notifications_source_record_id", "user_notifications", ["source_record_id"]
        )
        op.create_index("ix_user_notifications_created_at", "user_notifications", ["created_at"])

    if "notification_preferences" not in tables:
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("notification_type", sa.String(64), nullable=False),
            sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint(
                "user_id",
                "organization_id",
                "notification_type",
                name="uq_notification_preferences_user_type",
            ),
        )
        op.create_index(
            "ix_notification_preferences_user_id", "notification_preferences", ["user_id"]
        )
        op.create_index(
            "ix_notification_preferences_organization_id",
            "notification_preferences",
            ["organization_id"],
        )

    if "notification_delivery_attempts" not in tables:
        op.create_table(
            "notification_delivery_attempts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("notification_id", sa.String(36), nullable=False),
            sa.Column("notification_type", sa.String(64), nullable=False),
            sa.Column("channel", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("provider", sa.String(64), nullable=False),
            sa.Column("provider_message_id", sa.String(200), nullable=False, server_default=""),
            sa.Column("recipient", sa.String(320), nullable=False, server_default=""),
            sa.Column("subject", sa.String(500), nullable=False, server_default=""),
            sa.Column("diagnostics_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_notification_delivery_attempts_organization_id",
            "notification_delivery_attempts",
            ["organization_id"],
        )
        op.create_index(
            "ix_notification_delivery_attempts_user_id",
            "notification_delivery_attempts",
            ["user_id"],
        )
        op.create_index(
            "ix_notification_delivery_attempts_notification_id",
            "notification_delivery_attempts",
            ["notification_id"],
        )
        op.create_index(
            "ix_notification_delivery_attempts_status", "notification_delivery_attempts", ["status"]
        )
        op.create_index(
            "ix_notification_delivery_attempts_attempted_at",
            "notification_delivery_attempts",
            ["attempted_at"],
        )


def downgrade() -> None:
    op.drop_table("notification_delivery_attempts")
    op.drop_table("notification_preferences")
    op.drop_table("user_notifications")
