"""Tenant cache key isolation."""

from energy_core.cache.service import site_dashboard_cache_key, site_snapshot_cache_key


def test_cache_keys_include_tenant_prefix_when_provided() -> None:
    assert site_snapshot_cache_key(1, tenant_id=7) == "tenant:7:emic:site:1:snapshot"
    assert site_dashboard_cache_key(2, tenant_id=3) == "tenant:3:emic:site:2:dashboard"


def test_cache_keys_without_tenant_remain_backward_compatible() -> None:
    assert site_snapshot_cache_key(1) == "emic:site:1:snapshot"
