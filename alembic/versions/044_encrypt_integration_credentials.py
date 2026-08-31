"""Rename credential columns and encrypt existing values when EMIC_SECRET_KEY is set."""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op

revision = "044_encrypt_credentials"
down_revision = "043_heartbeat_ev_mappings_unique"
branch_labels = None
depends_on = None


def _encrypt_column(table: str, column: str, *, pk_column: str = "id") -> None:
    env_key = os.environ.get("EMIC_SECRET_KEY", "").strip()
    if not env_key:
        return

    from energy_core.secrets import CredentialCipher, SecretBox

    cipher = CredentialCipher(SecretBox(_normalize_key(env_key)))
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(f"SELECT {pk_column}, {column} FROM {table} WHERE {column} != ''")
    ).fetchall()
    for row_id, value in rows:
        encrypted = cipher.encrypt(value)
        if encrypted != value:
            conn.execute(
                sa.text(f"UPDATE {table} SET {column} = :encrypted WHERE {pk_column} = :row_id"),
                {"encrypted": encrypted, "row_id": row_id},
            )


def _normalize_key(raw: str) -> bytes:
    return raw.encode("ascii")


def upgrade() -> None:
    with op.batch_alter_table("ev_chargers") as batch:
        batch.alter_column(
            "chargeamps_api_key",
            new_column_name="encrypted_chargeamps_api_key",
            existing_type=sa.String(length=512),
            type_=sa.Text(),
            existing_nullable=False,
            server_default="",
        )
    with op.batch_alter_table("heartbeat_settings") as batch:
        batch.alter_column(
            "password",
            new_column_name="encrypted_password",
            existing_type=sa.String(length=512),
            type_=sa.Text(),
            existing_nullable=False,
            server_default="",
        )
        batch.alter_column(
            "api_token",
            new_column_name="encrypted_api_token",
            existing_type=sa.Text(),
            existing_nullable=False,
            server_default="",
        )
    with op.batch_alter_table("spa_device_config") as batch:
        batch.alter_column(
            "api_key",
            new_column_name="encrypted_api_key",
            existing_type=sa.String(length=512),
            type_=sa.Text(),
            existing_nullable=False,
            server_default="",
        )

    _encrypt_column("ev_chargers", "encrypted_chargeamps_api_key")
    _encrypt_column("heartbeat_settings", "encrypted_password")
    _encrypt_column("heartbeat_settings", "encrypted_api_token")
    _encrypt_column("spa_device_config", "encrypted_api_key", pk_column="consumer_id")


def downgrade() -> None:
    with op.batch_alter_table("spa_device_config") as batch:
        batch.alter_column(
            "encrypted_api_key",
            new_column_name="api_key",
            existing_type=sa.Text(),
            type_=sa.String(length=512),
            existing_nullable=False,
            server_default="",
        )
    with op.batch_alter_table("heartbeat_settings") as batch:
        batch.alter_column(
            "encrypted_api_token",
            new_column_name="api_token",
            existing_type=sa.Text(),
            existing_nullable=False,
            server_default="",
        )
        batch.alter_column(
            "encrypted_password",
            new_column_name="password",
            existing_type=sa.Text(),
            type_=sa.String(length=512),
            existing_nullable=False,
            server_default="",
        )
    with op.batch_alter_table("ev_chargers") as batch:
        batch.alter_column(
            "encrypted_chargeamps_api_key",
            new_column_name="chargeamps_api_key",
            existing_type=sa.Text(),
            type_=sa.String(length=512),
            existing_nullable=False,
            server_default="",
        )
