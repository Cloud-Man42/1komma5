"""Linux revocation and advisory E2E tests (F-RV-04)."""

from __future__ import annotations

import sys

import pytest

from energy_core.platform.modules.governance.types import RevocationMatch
from energy_core.platform.modules.isolation.security_monitor import RuntimeSecurityMonitor
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeEventType
from energy_core.platform.modules.marketplace.types import MetadataHealth
from energy_core.platform.modules.supply_chain.advisory_policy import merge_advisory_bundles, parse_advisory_bundle

from isolation_linux_helpers import cleanup_sandbox_env, start_runtime_with_mode


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux revocation E2E requires bwrap")
@pytest.mark.asyncio
async def test_publisher_revocation_e2e(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap", "marketplace_metadata_enabled": True})
    manager, runtime_id, _ = await start_runtime_with_mode(session, settings, session_factory, mode="benign")
    monitor = RuntimeSecurityMonitor(session, settings)
    monitor._revocations.load_context = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock(
        return_value=__import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(
            metadata_health=MetadataHealth.HEALTHY.value,
            revocations=(
                RevocationMatch(
                    revocation_id="rev-pub",
                    severity="HIGH",
                    scope="publisher",
                    publisher_id="emic-tests",
                    module_id=None,
                ),
            ),
        )
    )
    monitor._revocations.find_active_revocation = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(
        return_value=RevocationMatch(
            revocation_id="rev-pub",
            severity="HIGH",
            scope="publisher",
            publisher_id="emic-tests",
            module_id=None,
        )
    )
    try:
        assert await monitor.check_runtime(manager, runtime_id) is True
        record = await manager.get_runtime(runtime_id)
        assert record is not None
        assert record.state == IsolatedRuntimeState.QUARANTINED
        assert not manager.gateway.session_store.has_active_session(runtime_id)
    finally:
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux revocation E2E requires bwrap")
@pytest.mark.asyncio
async def test_module_revocation_e2e(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap", "marketplace_metadata_enabled": True})
    manager, runtime_id, _ = await start_runtime_with_mode(session, settings, session_factory, mode="benign")
    monitor = RuntimeSecurityMonitor(session, settings)
    from unittest.mock import AsyncMock, MagicMock

    monitor._revocations.load_context = AsyncMock(
        return_value=MagicMock(metadata_health=MetadataHealth.HEALTHY.value, revocations=())
    )
    monitor._revocations.find_active_revocation = MagicMock(
        return_value=RevocationMatch(
            revocation_id="rev-mod",
            severity="HIGH",
            scope="module",
            publisher_id=None,
            module_id="integration.sandbox-demo",
        )
    )
    try:
        assert await monitor.check_runtime(manager, runtime_id) is True
        record = await manager.get_runtime(runtime_id)
        assert record.state == IsolatedRuntimeState.QUARANTINED
    finally:
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux revocation E2E requires bwrap")
@pytest.mark.asyncio
async def test_critical_advisory_e2e(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap", "marketplace_metadata_enabled": True})
    manager, runtime_id, _ = await start_runtime_with_mode(session, settings, session_factory, mode="benign")
    monitor = RuntimeSecurityMonitor(session, settings)
    from unittest.mock import AsyncMock, MagicMock

    monitor._revocations.load_context = AsyncMock(
        return_value=MagicMock(metadata_health=MetadataHealth.HEALTHY.value, revocations=())
    )
    monitor._revocations.find_active_revocation = MagicMock(return_value=None)
    monitor._trust_cache.get_or_create = AsyncMock(return_value=MagicMock())
    monitor._trust_cache.parse_advisories = MagicMock(
        return_value={
            "bundle": {"generation": 1, "generated_at": "2026-09-08T12:00:00Z"},
            "advisories": [
                {
                    "advisory_id": "adv-crit",
                    "severity": "CRITICAL",
                    "status": "ACTIVE",
                    "affected": {
                        "purl": "pkg:emic/integration.sandbox-demo@1.0.0",
                        "version_range": ">=1.0.0",
                    },
                }
            ],
        }
    )
    try:
        assert await monitor.check_runtime(manager, runtime_id) is True
        record = await manager.get_runtime(runtime_id)
        assert record.state == IsolatedRuntimeState.QUARANTINED
    finally:
        cleanup_sandbox_env()


def test_advisory_r3_regression_higher_generation_retains_active():
    trusted = {
        "bundle": {"generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
        "advisories": [
            {
                "advisory_id": "adv-a1",
                "severity": "CRITICAL",
                "status": "ACTIVE",
                "affected": {"purl": "pkg:emic/integration.sandbox-demo@1.0.0", "version_range": ">=1.0.0"},
            }
        ],
    }
    incoming = parse_advisory_bundle(
        {
            "bundle": {"generation": 3, "generated_at": "2026-09-08T12:00:00Z"},
            "advisories": [],
        }
    )
    merged = merge_advisory_bundles(trusted_raw=trusted, incoming=incoming, incoming_raw=trusted)
    ids = {item["advisory_id"] for item in merged["advisories"]}
    assert "adv-a1" in ids
