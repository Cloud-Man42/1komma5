"""PostgreSQL RLS table classification helpers."""

from __future__ import annotations

# Tables with direct tenant_id column — policy tenant_isolation (migration 080).
DIRECT_TENANT_RLS_TABLES: frozenset[str] = frozenset(
    {
        "sites",
        "heartbeat_accounts",
        "emic_auth_audit_events",
        "tenant_users",
    }
)

# Never apply site-scoped RLS (global auth, tenancy meta, Timescale hypertables).
SITE_RLS_SKIP_TABLES: frozenset[str] = frozenset(
    {
        *DIRECT_TENANT_RLS_TABLES,
        "tenants",
        "tenant_user_roles",
        "tenant_user_site_access",
        "platform_user_roles",
        "emic_users",
        "emic_roles",
        "emic_permissions",
        "emic_user_roles",
        "emic_role_permissions",
        "emic_user_site_access",
        "emic_user_sessions",
        "emic_user_site_preferences",
        # energy_readings: migration 082 attempts tenant_id RLS; may remain disabled on Timescale.
        "energy_readings",
        "energy_hourly",
        "energy_daily",
    }
)


def _tenant_id_setting_sql() -> str:
    return "NULLIF(current_setting('app.current_tenant_id', true), '')::int"


def direct_tenant_rls_policy_sql(table: str) -> str:
    tenant_match = _tenant_id_setting_sql()
    return f"""
CREATE POLICY tenant_isolation ON "{table}"
USING (
    current_setting('app.platform_bypass', true) = 'true'
    OR (
        tenant_id IS NOT NULL
        AND tenant_id = {tenant_match}
    )
)
WITH CHECK (
    current_setting('app.platform_bypass', true) = 'true'
    OR (
        tenant_id IS NOT NULL
        AND tenant_id = {tenant_match}
    )
)
"""


def site_scoped_rls_policy_sql(table: str) -> str:
    tenant_match = _tenant_id_setting_sql()
    return f"""
CREATE POLICY tenant_site_isolation ON "{table}"
USING (
    current_setting('app.platform_bypass', true) = 'true'
    OR site_id IN (
        SELECT s.id FROM sites s
        WHERE s.tenant_id = {tenant_match}
    )
)
WITH CHECK (
    current_setting('app.platform_bypass', true) = 'true'
    OR site_id IN (
        SELECT s.id FROM sites s
        WHERE s.tenant_id = {tenant_match}
    )
)
"""
