"""PostgreSQL RLS integration tests (skipped unless TEST_POSTGRES_URL is set)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL required")


def test_rls_blocks_cross_tenant_select() -> None:
    postgres_url = os.environ["TEST_POSTGRES_URL"].replace("+asyncpg", "").replace("+psycopg", "")
    engine = create_engine(postgres_url)
    with engine.begin() as conn:
        tenant_a = conn.execute(
            text("SELECT id FROM tenants WHERE slug = 'henrik-home' LIMIT 1")
        ).scalar_one_or_none()
        if tenant_a is None:
            pytest.skip("henrik-home tenant not seeded in test database")
        other = conn.execute(
            text("SELECT id FROM sites WHERE tenant_id != :tid LIMIT 1"), {"tid": tenant_a}
        ).scalar_one_or_none()
        if other is None:
            pytest.skip("Need at least two tenants with sites for RLS cross-tenant test")
        conn.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"), {"tid": str(tenant_a)})
        blocked = conn.execute(
            text("SELECT COUNT(*) FROM sites WHERE tenant_id != :tid"), {"tid": tenant_a}
        ).scalar_one()
        assert blocked == 0
    engine.dispose()


def test_rls_pool_reset_clears_tenant_binding() -> None:
    postgres_url = os.environ["TEST_POSTGRES_URL"].replace("+asyncpg", "").replace("+psycopg", "")
    engine = create_engine(postgres_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.current_tenant_id', '1', true)"))
        conn.execute(text("RESET ALL"))
        cleared = conn.execute(text("SELECT current_setting('app.current_tenant_id', true)")).scalar()
        assert cleared in (None, "")
    engine.dispose()


def test_site_scoped_rls_enabled_on_child_tables() -> None:
    postgres_url = os.environ["TEST_POSTGRES_URL"].replace("+asyncpg", "").replace("+psycopg", "")
    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        enabled = conn.execute(
            text(
                """
                SELECT c.relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = 'ev_chargers'
                """
            )
        ).scalar_one_or_none()
        if enabled is None:
            pytest.skip("ev_chargers table missing in test database")
        assert enabled is True
    engine.dispose()
