"""Adversarial sandbox probe tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.types import RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages


async def _start_with_mode(session, settings, session_factory, mode: str) -> tuple[IsolatedModuleRuntimeManager, str, Path]:
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    os.environ["EMIC_SANDBOX_MODE"] = mode
    manager = IsolatedModuleRuntimeManager(session, settings)
    result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
    assert result.ok, result.message
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    data_path = Path(record.data_path or settings.resolved_isolated_runtime_data_root())
    return manager, result.runtime_instance_id, data_path


def _read_probes(data_root: Path, module_id: str, site_id: int, runtime_id: str) -> dict[str, str]:
    probe_path = data_root / module_id / str(site_id) / runtime_id / "probes.json"
    if not probe_path.exists():
        for candidate in data_root.rglob("probes.json"):
            probe_path = candidate
            break
    assert probe_path.exists(), f"probes.json missing under {data_root}"
    return json.loads(probe_path.read_text(encoding="utf-8"))


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_filesystem_probe_matrix(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, data_root = await _start_with_mode(session, settings, session_factory, "probe_filesystem")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["/etc/passwd"].startswith("denied")
        assert probes["/etc/shadow"].startswith("denied")
        assert probes["/var/run/docker.sock"].startswith("denied")
        assert probes["/package/manifest.json"] in {"allowed", "empty"}
        assert probes["/package/manifest.json.write"].startswith("denied")
        assert probes["/data/probes.json.write"] == "allowed"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_environment_scrub_probe(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_env")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        for key, value in probes.items():
            assert value == "absent", f"{key} leaked into worker environment"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_runtime_not_root(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_uid")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["uid"] != "0"
        assert probes["euid"] != "0"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_evil_network_denied(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "evil_network")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["network"].startswith("denied")
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)
