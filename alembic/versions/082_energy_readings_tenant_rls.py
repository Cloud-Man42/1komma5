"""082 — Optional tenant_id RLS on energy_readings (skipped on Timescale columnstore)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from energy_core.tenancy.rls_tables import direct_tenant_rls_policy_sql
from sqlalchemy import inspect

revision = "082_energy_readings_tenant_rls"
down_revision = "081_site_scoped_rls_policies"
branch_labels = None
depends_on = None

TABLE = "energy_readings"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    conn = op.get_bind()
    if TABLE not in inspect(conn).get_table_names():
        return
    columns = {c["name"] for c in inspect(conn).get_columns(TABLE)}
    if "tenant_id" not in columns:
        return
    conn.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Skipping {TABLE} RLS enable: %', SQLERRM;
            END $$;
            """
        )
    )
    enabled = conn.execute(
        sa.text(
            """
            SELECT c.relrowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = current_schema() AND c.relname = :table_name
            """
        ),
        {"table_name": TABLE},
    ).scalar()
    if not enabled:
        return
    conn.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{TABLE}"'))
    conn.execute(sa.text(direct_tenant_rls_policy_sql(TABLE)))


def downgrade() -> None:
    if not _is_postgres():
        return
    conn = op.get_bind()
    if TABLE not in inspect(conn).get_table_names():
        return
    conn.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{TABLE}"'))
    conn.execute(sa.text(f'ALTER TABLE "{TABLE}" DISABLE ROW LEVEL SECURITY'))
