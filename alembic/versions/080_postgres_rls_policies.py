"""080 — PostgreSQL row-level security policies (no-op on SQLite)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "080_postgres_rls_policies"
down_revision = "079_tenants_foundation"
branch_labels = None
depends_on = None

RLS_TABLES_WITH_TENANT_ID = (
    "sites",
    # energy_readings is a Timescale hypertable with columnstore — RLS not supported.
    "heartbeat_accounts",
    "emic_auth_audit_events",
    "tenant_users",
)


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _is_postgres():
        return
    conn = op.get_bind()
    for table in RLS_TABLES_WITH_TENANT_ID:
        if table not in _table_names() or "tenant_id" not in _column_names(table):
            continue
        conn.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        conn.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY tenant_isolation ON "{table}"
                USING (
                    current_setting('app.platform_bypass', true) = 'true'
                    OR (
                        tenant_id IS NOT NULL
                        AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::int
                    )
                )
                WITH CHECK (
                    current_setting('app.platform_bypass', true) = 'true'
                    OR (
                        tenant_id IS NOT NULL
                        AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::int
                    )
                )
                """
            )
        )


def downgrade() -> None:
    if not _is_postgres():
        return
    conn = op.get_bind()
    for table in RLS_TABLES_WITH_TENANT_ID:
        if table not in _table_names():
            continue
        conn.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
        conn.execute(sa.text(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY'))
