"""Internationalization and timezone baseline (US-047) — durable
`users.locale`, `users.timezone`,
`organizations.default_locale`, and
`organizations.default_timezone` columns. The
migration is additive; the documented rollback
path is to drop the four columns. No existing
rows are touched.

Revision ID: 20260616_0037
Revises: 20260616_0036
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0037"
down_revision: str | Sequence[str] | None = "20260616_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not _has_table(table_name):
        return False
    return column_name in {c["name"] for c in insp.get_columns(table_name)}


def upgrade() -> None:
    # users.locale
    if _has_table("users") and not _has_column("users", "locale"):
        with op.batch_alter_table("users") as batch:
            batch.add_column(
                sa.Column(
                    "locale",
                    sa.String(length=16),
                    nullable=False,
                    server_default="en-US",
                )
            )
    # users.timezone
    if _has_table("users") and not _has_column("users", "timezone"):
        with op.batch_alter_table("users") as batch:
            batch.add_column(
                sa.Column(
                    "timezone",
                    sa.String(length=64),
                    nullable=False,
                    server_default="UTC",
                )
            )
    # organizations.default_locale
    if _has_table("organizations") and not _has_column(
        "organizations", "default_locale"
    ):
        with op.batch_alter_table("organizations") as batch:
            batch.add_column(
                sa.Column(
                    "default_locale",
                    sa.String(length=16),
                    nullable=False,
                    server_default="en-US",
                )
            )
    # organizations.default_timezone
    if _has_table("organizations") and not _has_column(
        "organizations", "default_timezone"
    ):
        with op.batch_alter_table("organizations") as batch:
            batch.add_column(
                sa.Column(
                    "default_timezone",
                    sa.String(length=64),
                    nullable=False,
                    server_default="UTC",
                )
            )


def downgrade() -> None:
    if _has_table("organizations") and _has_column(
        "organizations", "default_timezone"
    ):
        with op.batch_alter_table("organizations") as batch:
            batch.drop_column("default_timezone")
    if _has_table("organizations") and _has_column(
        "organizations", "default_locale"
    ):
        with op.batch_alter_table("organizations") as batch:
            batch.drop_column("default_locale")
    if _has_table("users") and _has_column("users", "timezone"):
        with op.batch_alter_table("users") as batch:
            batch.drop_column("timezone")
    if _has_table("users") and _has_column("users", "locale"):
        with op.batch_alter_table("users") as batch:
            batch.drop_column("locale")
