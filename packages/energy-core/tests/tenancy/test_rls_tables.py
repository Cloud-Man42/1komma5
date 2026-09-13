"""RLS table classification tests."""

from __future__ import annotations

from energy_core.tenancy.rls_tables import (
    DIRECT_TENANT_RLS_TABLES,
    SITE_RLS_SKIP_TABLES,
    direct_tenant_rls_policy_sql,
    site_scoped_rls_policy_sql,
)


def test_direct_tenant_tables_not_in_site_skip_overlap() -> None:
    assert DIRECT_TENANT_RLS_TABLES.issubset(SITE_RLS_SKIP_TABLES)


def test_site_scoped_policy_references_sites_subquery() -> None:
    sql = site_scoped_rls_policy_sql("ev_chargers")
    assert "tenant_site_isolation" in sql
    assert "FROM sites s" in sql
    assert "app.current_tenant_id" in sql


def test_direct_tenant_policy_matches_tenant_id() -> None:
    sql = direct_tenant_rls_policy_sql("sites")
    assert "tenant_isolation" in sql
    assert "tenant_id =" in sql
    assert "app.platform_bypass" in sql
