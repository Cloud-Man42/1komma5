"""073 — multi-account Heartbeat: heartbeat_accounts + site mapping columns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "073_heartbeat_multi_account"
down_revision = "072_sensibo_site_config"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "heartbeat_accounts" not in _table_names():
        op.create_table(
            "heartbeat_accounts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False, server_default="1komma5"),
            sa.Column("connection_type", sa.String(length=16), nullable=False, server_default="cloud"),
            sa.Column("host", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
            sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("api_path", sa.String(length=128), nullable=False, server_default="/api"),
            sa.Column("username", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("encrypted_password", sa.Text(), nullable=False, server_default=""),
            sa.Column("encrypted_api_token", sa.Text(), nullable=False, server_default=""),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_authentication_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_successful_authentication_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_authentication_error", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("slug", name="uq_heartbeat_accounts_slug"),
        )
        op.create_index("ix_heartbeat_accounts_slug", "heartbeat_accounts", ["slug"], unique=True)

    site_cols = {c["name"] for c in inspect(op.get_bind()).get_columns("sites")}
    new_site_columns = [
        ("heartbeat_account_id", sa.Integer(), True),
        ("heartbeat_site_id", sa.String(length=128), False),
        ("heartbeat_system_id", sa.String(length=128), False),
        ("heartbeat_asset_id", sa.String(length=128), False),
        ("heartbeat_device_id", sa.String(length=128), False),
        ("heartbeat_serial_number", sa.String(length=128), False),
    ]
    missing = [(name, col_type, is_fk) for name, col_type, is_fk in new_site_columns if name not in site_cols]
    if missing:
        with op.batch_alter_table("sites") as batch:
            for name, col_type, is_fk in missing:
                batch.add_column(sa.Column(name, col_type, nullable=True))
            if any(name == "heartbeat_account_id" for name, _, is_fk in missing if is_fk):
                batch.create_foreign_key(
                    "fk_sites_heartbeat_account_id",
                    "heartbeat_accounts",
                    ["heartbeat_account_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if any(name == "heartbeat_account_id" for name, _, _ in missing):
            op.create_index("ix_sites_heartbeat_account_id", "sites", ["heartbeat_account_id"])

    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        existing = conn.execute(text("SELECT id FROM heartbeat_accounts WHERE slug = 'default'")).fetchone()
    else:
        existing = conn.execute(text("SELECT id FROM heartbeat_accounts WHERE slug = 'default' LIMIT 1")).fetchone()

    if existing is None and "heartbeat_settings" in _table_names():
        conn.execute(
            text(
                """
                INSERT INTO heartbeat_accounts (
                    slug, name, provider, connection_type, host, port, use_tls, api_path,
                    username, encrypted_password, encrypted_api_token, is_enabled
                )
                SELECT
                    'default',
                    'Default Heartbeat Account',
                    '1komma5',
                    connection_type,
                    host,
                    port,
                    use_tls,
                    api_path,
                    username,
                    encrypted_password,
                    encrypted_api_token,
                    TRUE
                FROM heartbeat_settings
                WHERE id = 1
                """
            )
        )

    if conn.dialect.name == "sqlite":
        default_row = conn.execute(text("SELECT id FROM heartbeat_accounts WHERE slug = 'default'")).fetchone()
    else:
        default_row = conn.execute(text("SELECT id FROM heartbeat_accounts WHERE slug = 'default' LIMIT 1")).fetchone()

    if default_row is not None:
        default_id = default_row[0]
        conn.execute(
            text(
                """
                UPDATE sites
                SET heartbeat_account_id = :aid,
                    heartbeat_system_id = COALESCE(heartbeat_system_id, external_system_id)
                WHERE external_system_id IS NOT NULL
                  AND heartbeat_account_id IS NULL
                """
            ),
            {"aid": default_id},
        )


def downgrade() -> None:
    if "sites" in _table_names():
        cols = {c["name"] for c in inspect(op.get_bind()).get_columns("sites")}
        drop_cols = [
            "heartbeat_serial_number",
            "heartbeat_device_id",
            "heartbeat_asset_id",
            "heartbeat_system_id",
            "heartbeat_site_id",
            "heartbeat_account_id",
        ]
        to_drop = [col for col in drop_cols if col in cols]
        if to_drop:
            with op.batch_alter_table("sites") as batch:
                for col in to_drop:
                    batch.drop_column(col)
            if "heartbeat_account_id" in to_drop:
                op.drop_index("ix_sites_heartbeat_account_id", table_name="sites")
    if "heartbeat_accounts" in _table_names():
        op.drop_index("ix_heartbeat_accounts_slug", table_name="heartbeat_accounts")
        op.drop_table("heartbeat_accounts")
