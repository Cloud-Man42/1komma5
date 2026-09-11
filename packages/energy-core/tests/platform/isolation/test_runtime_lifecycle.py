"""Runtime manager lifecycle tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages


@pytest.mark.asyncio
async def test_runtime_blocked_when_disabled(isolation_session):
    session, settings, session_factory = isolation_session
    settings.third_party_runtime_enabled = False
    settings.isolated_runtime_enabled = False
    manager = IsolatedModuleRuntimeManager(session, settings)
    result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
    assert not result.ok
    assert result.state == IsolatedRuntimeState.BLOCKED


@pytest.mark.asyncio
async def test_isolated_runtime_start_and_stop(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    manager = IsolatedModuleRuntimeManager(session, settings)
    result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
    assert result.ok, result.message
    assert result.state == IsolatedRuntimeState.RUNNING
    await manager.stop_runtime(result.runtime_instance_id)
    await session.commit()
    stopped = await manager.get_runtime(result.runtime_instance_id)
    assert stopped is not None
    assert stopped.state == IsolatedRuntimeState.STOPPED


@pytest.mark.asyncio
async def test_control_gate_blocks_without_isolation_open(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
    from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
    from energy_core.platform.modules.governance.types import PolicyAction

    assert ModuleInstallPolicyEngine.CONTROL_ISOLATION_GATE_OPEN is False
    result = await GovernanceEvaluationService(session).evaluate(
        action=PolicyAction.RUN,
        module_id="integration.control-demo",
        publisher_id="emic-tests",
        permissions=("device.control",),
        provided_capabilities=("device.control",),
        marketplace_enabled=False,
        app_env_production=True,
    )
    assert result.control_capable is True
    assert result.decision.value == "DENY"
    assert "CONTROL_MODULE_ISOLATION_REQUIRED" in result.reason_codes
