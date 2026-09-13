"""081 — PostgreSQL RLS for site-scoped child tables (no-op on SQLite)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from energy_core.tenancy.rls_tables import SITE_RLS_SKIP_TABLES, site_scoped_rls_policy_sql

revision = "081_site_scoped_rls_policies"
down_revision = "080_postgres_rls_policies"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _tables_with_site_id() -> list[str]:
    names: list[str] = []
    for table in inspect(op.get_bind()).get_table_names():
        if table in SITE_RLS_SKIP_TABLES:
            continue
        columns = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
        if "site_id" in columns:
            names.append(table)
    return sorted(names)


def upgrade() -> None:
    if not _is_postgres():
        return
    conn = op.get_bind()
    for table in _tables_with_site_id():
        conn.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        conn.execute(sa.text(f'DROP POLICY IF EXISTS tenant_site_isolation ON "{table}"'))
        conn.execute(sa.text(site_scoped_rls_policy_sql(table)))


def downgrade() -> None:
    if not _is_postgres():
        return
    conn = op.get_bind()
    for table in _tables_with_site_id():
        conn.execute(sa.text(f'DROP POLICY IF EXISTS tenant_site_isolation ON "{table}"'))
        conn.execute(sa.text(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY'))
