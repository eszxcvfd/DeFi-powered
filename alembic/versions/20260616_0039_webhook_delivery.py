"""Governed webhook delivery baseline (US-049) —
durable `webhook_subscriptions`,
`webhook_signing_secrets`, and
`webhook_deliveries` tables. The migration
is additive; the documented rollback path
is to drop the new tables. No existing rows
are touched.

Revision ID: 20260616_0039
Revises: 20260616_0038
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0039"
down_revision: str | Sequence[str] | None = "20260616_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def upgrade() -> None:
    if not _has_table("webhook_subscriptions"):
        op.create_table(
            "webhook_subscriptions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column(
                "target_url", sa.String(length=2048), nullable=False
            ),
            sa.Column(
                "secret_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "event_types_json",
                sa.Text(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_by",
                sa.String(length=128),
                nullable=False,
                server_default="system",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "last_rotated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_success_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_failure_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_webhook_subscriptions_org",
            "webhook_subscriptions",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_webhook_subscriptions_org_enabled",
            "webhook_subscriptions",
            ["organization_id", "enabled"],
            unique=False,
        )

    if not _has_table("webhook_signing_secrets"):
        op.create_table(
            "webhook_signing_secrets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "subscription_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "secret_ciphertext", sa.Text(), nullable=False
            ),
            sa.Column(
                "version", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "rotated_at", sa.DateTime(timezone=True), nullable=True
            ),
        )
        op.create_index(
            "ix_webhook_signing_secrets_org",
            "webhook_signing_secrets",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_webhook_signing_secrets_sub",
            "webhook_signing_secrets",
            ["organization_id", "subscription_id"],
            unique=False,
        )

    if not _has_table("webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "subscription_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "event_id", sa.String(length=64), nullable=True
            ),
            sa.Column(
                "event_type", sa.String(length=64), nullable=False
            ),
            sa.Column(
                "target_url", sa.String(length=2048), nullable=False
            ),
            sa.Column(
                "payload_hash", sa.String(length=64), nullable=False
            ),
            sa.Column(
                "request_body", sa.Text(), nullable=False, server_default=""
            ),
            sa.Column(
                "signature", sa.String(length=256), nullable=False, server_default=""
            ),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "attempt_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "next_attempt_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_attempt_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_response_code", sa.Integer(), nullable=True
            ),
            sa.Column(
                "last_response_message", sa.Text(), nullable=True
            ),
            sa.Column(
                "delivered_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_webhook_deliveries_org",
            "webhook_deliveries",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_webhook_deliveries_sub",
            "webhook_deliveries",
            ["organization_id", "subscription_id", "created_at"],
            unique=False,
        )
        op.create_index(
            "ix_webhook_deliveries_status",
            "webhook_deliveries",
            ["organization_id", "status", "next_attempt_at"],
            unique=False,
        )
        op.create_index(
            "ix_webhook_deliveries_next",
            "webhook_deliveries",
            ["next_attempt_at"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("webhook_deliveries"):
        op.drop_table("webhook_deliveries")
    if _has_table("webhook_signing_secrets"):
        op.drop_table("webhook_signing_secrets")
    if _has_table("webhook_subscriptions"):
        op.drop_table("webhook_subscriptions")
