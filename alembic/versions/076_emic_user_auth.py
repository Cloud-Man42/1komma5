"""076 — EMIC user auth tables (users, RBAC, sessions, auth audit)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "076_emic_user_auth"
down_revision = "075_heartbeat_account_api_audit"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "emic_users" not in _table_names():
        op.create_table(
            "emic_users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("username_normalized", sa.String(length=64), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("email_normalized", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("first_name", sa.String(length=128), nullable=True),
            sa.Column("last_name", sa.String(length=128), nullable=True),
            sa.Column("display_name", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lockout_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_successful_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
            sa.UniqueConstraint("username_normalized"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("email_normalized"),
        )
        op.create_index("ix_emic_users_username", "emic_users", ["username"])
        op.create_index("ix_emic_users_email", "emic_users", ["email"])

    if "emic_roles" not in _table_names():
        op.create_table(
            "emic_roles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index("ix_emic_roles_name", "emic_roles", ["name"])

    if "emic_permissions" not in _table_names():
        op.create_table(
            "emic_permissions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("group_name", sa.String(length=64), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )
        op.create_index("ix_emic_permissions_key", "emic_permissions", ["key"])

    if "emic_user_roles" not in _table_names():
        op.create_table(
            "emic_user_roles",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["emic_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["emic_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "role_id"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_emic_user_roles"),
        )

    if "emic_role_permissions" not in _table_names():
        op.create_table(
            "emic_role_permissions",
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["permission_id"], ["emic_permissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["emic_roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_id", "permission_id"),
            sa.UniqueConstraint("role_id", "permission_id", name="uq_emic_role_permissions"),
        )

    if "emic_user_site_access" not in _table_names():
        op.create_table(
            "emic_user_site_access",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["emic_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "site_id", name="uq_emic_user_site_access"),
        )
        op.create_index("ix_emic_user_site_access_user_id", "emic_user_site_access", ["user_id"])
        op.create_index("ix_emic_user_site_access_site_id", "emic_user_site_access", ["site_id"])

    if "emic_user_sessions" not in _table_names():
        op.create_table(
            "emic_user_sessions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("token_prefix", sa.String(length=16), nullable=False),
            sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_ip", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["emic_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_emic_user_sessions_token_hash", "emic_user_sessions", ["token_hash"])
        op.create_index("ix_emic_user_sessions_expires_at", "emic_user_sessions", ["expires_at"])

    if "emic_auth_audit_events" not in _table_names():
        op.create_table(
            "emic_auth_audit_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("username", sa.String(length=64), nullable=True),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("entity_type", sa.String(length=64), nullable=True),
            sa.Column("entity_id", sa.String(length=128), nullable=True),
            sa.Column("site_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("source_ip", sa.String(length=64), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["emic_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_emic_auth_audit_events_recorded_at", "emic_auth_audit_events", ["recorded_at"])
        op.create_index("ix_emic_auth_audit_events_event_type", "emic_auth_audit_events", ["event_type"])

    audit_cols = _column_names("admin_audit_log") if "admin_audit_log" in _table_names() else set()
    if "admin_audit_log" in _table_names():
        with op.batch_alter_table("admin_audit_log") as batch:
            if "actor_user_id" not in audit_cols:
                batch.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
            if "actor_type" not in audit_cols:
                batch.add_column(sa.Column("actor_type", sa.String(length=32), nullable=True))


def downgrade() -> None:
    if "admin_audit_log" in _table_names():
        cols = _column_names("admin_audit_log")
        with op.batch_alter_table("admin_audit_log") as batch:
            if "actor_type" in cols:
                batch.drop_column("actor_type")
            if "actor_user_id" in cols:
                batch.drop_column("actor_user_id")

    for table in (
        "emic_auth_audit_events",
        "emic_user_sessions",
        "emic_user_site_access",
        "emic_role_permissions",
        "emic_user_roles",
        "emic_permissions",
        "emic_roles",
        "emic_users",
    ):
        if table in _table_names():
            op.drop_table(table)
