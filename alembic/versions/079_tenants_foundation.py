"""079 — Multi-tenant foundation: tenants, membership, Henrik Home backfill."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "079_tenants_foundation"
down_revision = "078_denmark_main_fuse_50a"
branch_labels = None
depends_on = None

DEFAULT_TENANT_SLUG = "henrik-home"
DEFAULT_TENANT_NAME = "Henrik Home"


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "tenants" not in _table_names():
        op.create_table(
            "tenants",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=False),
            sa.Column("slug", sa.String(length=64), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Europe/Stockholm"),
            sa.Column("default_currency", sa.String(length=8), nullable=False, server_default="SEK"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index("ix_tenants_slug", "tenants", ["slug"])

    if "tenant_users" not in _table_names():
        op.create_table(
            "tenant_users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["emic_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_users_tenant_user"),
        )
        op.create_index("ix_tenant_users_tenant_id", "tenant_users", ["tenant_id"])
        op.create_index("ix_tenant_users_user_id", "tenant_users", ["user_id"])

    if "tenant_user_roles" not in _table_names():
        op.create_table(
            "tenant_user_roles",
            sa.Column("tenant_user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_user_id"], ["tenant_users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["emic_roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("tenant_user_id", "role_id"),
            sa.UniqueConstraint("tenant_user_id", "role_id", name="uq_tenant_user_roles"),
        )

    if "tenant_user_site_access" not in _table_names():
        op.create_table(
            "tenant_user_site_access",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_user_id", sa.Integer(), nullable=False),
            sa.Column("site_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_user_id"], ["tenant_users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_user_id", "site_id", name="uq_tenant_user_site_access"),
        )
        op.create_index("ix_tenant_user_site_access_tenant_user_id", "tenant_user_site_access", ["tenant_user_id"])
        op.create_index("ix_tenant_user_site_access_site_id", "tenant_user_site_access", ["site_id"])

    if "platform_user_roles" not in _table_names():
        op.create_table(
            "platform_user_roles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_name", sa.String(length=64), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["emic_users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "role_name", name="uq_platform_user_roles"),
        )
        op.create_index("ix_platform_user_roles_user_id", "platform_user_roles", ["user_id"])

    conn = op.get_bind()

    conn.execute(
        sa.text(
            "INSERT INTO tenants (name, display_name, slug, is_active, status, timezone, default_currency) "
            "SELECT :name, :display, :slug, true, 'active', 'Europe/Stockholm', 'SEK' "
            "WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE slug = :slug_exists)"
        ),
        {
            "name": DEFAULT_TENANT_NAME,
            "display": DEFAULT_TENANT_NAME,
            "slug": DEFAULT_TENANT_SLUG,
            "slug_exists": DEFAULT_TENANT_SLUG,
        },
    )

    if "sites" in _table_names() and "tenant_id" not in _column_names("sites"):
        with op.batch_alter_table("sites") as batch:
            batch.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_sites_tenant_id", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")

    if "heartbeat_accounts" in _table_names() and "tenant_id" not in _column_names("heartbeat_accounts"):
        with op.batch_alter_table("heartbeat_accounts") as batch:
            batch.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_heartbeat_accounts_tenant_id", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")

    if "emic_auth_audit_events" in _table_names() and "tenant_id" not in _column_names("emic_auth_audit_events"):
        with op.batch_alter_table("emic_auth_audit_events") as batch:
            batch.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_emic_auth_audit_tenant_id", "tenants", ["tenant_id"], ["id"], ondelete="SET NULL")

    if "emic_user_sessions" in _table_names() and "active_tenant_id" not in _column_names("emic_user_sessions"):
        with op.batch_alter_table("emic_user_sessions") as batch:
            batch.add_column(sa.Column("active_tenant_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_emic_user_sessions_active_tenant_id", "tenants", ["active_tenant_id"], ["id"], ondelete="SET NULL"
            )

    tenant_id = conn.execute(sa.text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": DEFAULT_TENANT_SLUG}).scalar()
    if tenant_id is not None:
        conn.execute(sa.text("UPDATE sites SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": tenant_id})
        conn.execute(
            sa.text("UPDATE heartbeat_accounts SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": tenant_id}
        )
        conn.execute(
            sa.text("UPDATE emic_auth_audit_events SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": tenant_id}
        )

        conn.execute(
            sa.text(
                """
                INSERT INTO tenant_users (tenant_id, user_id, is_active)
                SELECT :tid, u.id, u.is_active
                FROM emic_users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM tenant_users tu WHERE tu.tenant_id = :tid AND tu.user_id = u.id
                )
                """
            ),
            {"tid": tenant_id},
        )

        conn.execute(
            sa.text(
                """
                INSERT INTO tenant_user_roles (tenant_user_id, role_id)
                SELECT tu.id, ur.role_id
                FROM emic_user_roles ur
                JOIN tenant_users tu ON tu.user_id = ur.user_id AND tu.tenant_id = :tid
                WHERE NOT EXISTS (
                    SELECT 1 FROM tenant_user_roles tur
                    WHERE tur.tenant_user_id = tu.id AND tur.role_id = ur.role_id
                )
                """
            ),
            {"tid": tenant_id},
        )

        conn.execute(
            sa.text(
                """
                INSERT INTO tenant_user_site_access (tenant_user_id, site_id)
                SELECT tu.id, usa.site_id
                FROM emic_user_site_access usa
                JOIN tenant_users tu ON tu.user_id = usa.user_id AND tu.tenant_id = :tid
                JOIN sites s ON s.id = usa.site_id AND s.tenant_id = :tid
                WHERE NOT EXISTS (
                    SELECT 1 FROM tenant_user_site_access tusa
                    WHERE tusa.tenant_user_id = tu.id AND tusa.site_id = usa.site_id
                )
                """
            ),
            {"tid": tenant_id},
        )

        conn.execute(
            sa.text(
                """
                INSERT INTO platform_user_roles (user_id, role_name)
                SELECT DISTINCT ur.user_id, 'PLATFORM_SUPER_ADMIN'
                FROM emic_user_roles ur
                JOIN emic_roles r ON r.id = ur.role_id
                WHERE r.name = 'SUPER_ADMIN'
                AND NOT EXISTS (
                    SELECT 1 FROM platform_user_roles p
                    WHERE p.user_id = ur.user_id AND p.role_name = 'PLATFORM_SUPER_ADMIN'
                )
                """
            )
        )

        conn.execute(
            sa.text(
                "UPDATE emic_user_sessions SET active_tenant_id = :tid WHERE active_tenant_id IS NULL"
            ),
            {"tid": tenant_id},
        )

    if "sites" in _table_names() and "tenant_id" in _column_names("sites"):
        bind = op.get_bind()
        insp = inspect(bind)
        is_sqlite = bind.dialect.name == "sqlite"
        if is_sqlite:
            for idx in insp.get_indexes("sites"):
                if idx.get("unique") and list(idx.get("column_names") or []) == ["slug"]:
                    op.drop_index(idx["name"], table_name="sites")
        else:
            for uc in insp.get_unique_constraints("sites"):
                if list(uc.get("column_names") or []) == ["slug"]:
                    op.drop_constraint(uc["name"], "sites", type_="unique")
        with op.batch_alter_table("sites") as batch:
            batch.alter_column("tenant_id", nullable=False)
            batch.create_unique_constraint("uq_sites_tenant_slug", ["tenant_id", "slug"])

    if "energy_readings" in _table_names() and "tenant_id" not in _column_names("energy_readings"):
        with op.batch_alter_table("energy_readings") as batch:
            batch.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
        if bind.dialect.name == "postgresql":
            conn.execute(sa.text("SET LOCAL timescaledb.max_tuples_decompressed_per_dml_transaction = 0"))
        for site_id, site_tenant_id in conn.execute(sa.text("SELECT id, tenant_id FROM sites")).fetchall():
            conn.execute(
                sa.text(
                    "UPDATE energy_readings SET tenant_id = :tenant_id "
                    "WHERE site_id = :site_id AND tenant_id IS NULL"
                ),
                {"tenant_id": site_tenant_id, "site_id": site_id},
            )


def downgrade() -> None:
    if "energy_readings" in _table_names() and "tenant_id" in _column_names("energy_readings"):
        with op.batch_alter_table("energy_readings") as batch:
            batch.drop_column("tenant_id")

    if "sites" in _table_names() and "tenant_id" in _column_names("sites"):
        with op.batch_alter_table("sites") as batch:
            try:
                batch.drop_constraint("uq_sites_tenant_slug", type_="unique")
            except Exception:
                pass
            batch.create_unique_constraint("sites_slug_key", ["slug"])
            batch.drop_constraint("fk_sites_tenant_id", type_="foreignkey")
            batch.drop_column("tenant_id")

    for table, col, fk in [
        ("heartbeat_accounts", "tenant_id", "fk_heartbeat_accounts_tenant_id"),
        ("emic_auth_audit_events", "tenant_id", "fk_emic_auth_audit_tenant_id"),
        ("emic_user_sessions", "active_tenant_id", "fk_emic_user_sessions_active_tenant_id"),
    ]:
        if table in _table_names() and col in _column_names(table):
            with op.batch_alter_table(table) as batch:
                try:
                    batch.drop_constraint(fk, type_="foreignkey")
                except Exception:
                    pass
                batch.drop_column(col)

    for table in ("platform_user_roles", "tenant_user_site_access", "tenant_user_roles", "tenant_users", "tenants"):
        if table in _table_names():
            op.drop_table(table)
