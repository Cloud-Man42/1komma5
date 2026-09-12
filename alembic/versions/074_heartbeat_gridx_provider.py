"""074 — GridX provider auth fields + site gateway id."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "074_heartbeat_gridx_provider"
down_revision = "073_heartbeat_multi_account"
branch_labels = None
depends_on = None


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    account_cols = _column_names("heartbeat_accounts")
    account_additions = [
        ("encrypted_refresh_token", sa.Text(), ""),
        ("auth_domain", sa.String(length=255), ""),
        ("auth_realm", sa.String(length=128), ""),
        ("auth_client_id", sa.String(length=128), ""),
    ]
    missing_accounts = [(name, col_type, default) for name, col_type, default in account_additions if name not in account_cols]
    if missing_accounts:
        with op.batch_alter_table("heartbeat_accounts") as batch:
            for name, col_type, default in missing_accounts:
                batch.add_column(sa.Column(name, col_type, nullable=False, server_default=default))

    site_cols = _column_names("sites")
    if "heartbeat_gateway_id" not in site_cols:
        with op.batch_alter_table("sites") as batch:
            batch.add_column(sa.Column("heartbeat_gateway_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    site_cols = _column_names("sites")
    if "heartbeat_gateway_id" in site_cols:
        with op.batch_alter_table("sites") as batch:
            batch.drop_column("heartbeat_gateway_id")

    account_cols = _column_names("heartbeat_accounts")
    for name in ("auth_client_id", "auth_realm", "auth_domain", "encrypted_refresh_token"):
        if name in account_cols:
            with op.batch_alter_table("heartbeat_accounts") as batch:
                batch.drop_column(name)
