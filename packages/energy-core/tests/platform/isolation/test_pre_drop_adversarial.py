"""Pre-drop adversarial Linux security suite (F-RV-01 / F-RV-08)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeEventType, RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages

from isolation_linux_helpers import cleanup_sandbox_env, read_probes


async def _start_pre_drop(session, settings, session_factory, *, mode: str = "entrypoint", extra_env: dict[str, str] | None = None):
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    os.environ["EMIC_SANDBOX_MODE"] = mode
    for key, value in (extra_env or {}).items():
        os.environ[key] = value
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager = IsolatedModuleRuntimeManager(session, settings)
    result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.pre-drop-probe", site_id=1))
    return manager, result


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
def test_sitecustomize_not_executed_with_isolated_python(tmp_path):
    marker = tmp_path / "sitecustomize-fired"
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "sitecustomize.py").write_text(
        f'open(r"{marker}", "w", encoding="utf-8").write("1")',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site_dir)
    subprocess.run([sys.executable, "-I", "-s", "-c", "pass"], env=env, check=True)
    assert not marker.exists()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
def test_usercustomize_not_executed_with_isolated_python(tmp_path):
    marker = tmp_path / "usercustomize-fired"
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "usercustomize.py").write_text(
        f'open(r"{marker}", "w", encoding="utf-8").write("1")',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(site_dir)
    subprocess.run([sys.executable, "-I", "-s", "-c", "pass"], env=env, check=True)
    assert not marker.exists()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_malicious_entrypoint_low_privilege(pre_drop_probe_package, tmp_path):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(session, settings, session_factory, mode="entrypoint")
    assert result.ok, result.message
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    try:
        probes = read_probes(Path(record.data_path))
        assert probes["uid"] == "10001"
        assert probes["euid"] == "10001"
        assert probes["gid"] == "10001"
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_malicious_init_not_executed_before_drop(pre_drop_probe_package):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(session, settings, session_factory, mode="entrypoint")
    assert result.ok
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    init_probe = Path(record.data_path) / "init_probe.json"
    try:
        assert not init_probe.exists(), "package __init__ executed before explicit import"
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_malicious_init_low_privilege_when_imported(pre_drop_probe_package):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(session, settings, session_factory, mode="force_package_import")
    assert result.ok
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    try:
        probes = read_probes(Path(record.data_path))
        assert probes.get("init_imported") == "yes"
        assert str(probes.get("uid")) == "10001"
        assert str(probes.get("euid")) == "10001"
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_root_read_canary_denied(pre_drop_probe_package, tmp_path):
    canary = tmp_path / "emic-root-read-canary"
    canary.write_text("secret-canary", encoding="utf-8")
    os.chmod(canary, stat.S_IRUSR)
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(
        session,
        settings,
        session_factory,
        extra_env={"EMIC_PROBE_ROOT_READ_CANARY": str(canary)},
    )
    assert result.ok
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    try:
        probes = read_probes(Path(record.data_path))
        assert probes["root_read_canary"].startswith("denied")
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_root_write_canary_denied(pre_drop_probe_package, tmp_path):
    write_target = tmp_path / "emic-pre-drop-owned"
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(
        session,
        settings,
        session_factory,
        extra_env={"EMIC_PROBE_ROOT_WRITE_CANARY": str(write_target)},
    )
    assert result.ok
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    try:
        probes = read_probes(Path(record.data_path))
        assert probes["root_write_canary"].startswith("denied")
        assert not write_target.exists()
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_forced_setuid_failure_fail_closed(pre_drop_probe_package):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(
        session,
        settings,
        session_factory,
        extra_env={"EMIC_SANDBOX_FORCE_DROP_FAIL": "setuid"},
    )
    assert not result.ok
    await session.commit()
    repo = IsolatedRuntimeRepository(session)
    events = await repo.list_events(
        runtime_instance_id=result.runtime_instance_id,
        event_type=RuntimeEventType.PRIVILEGE_DROP_FAILED,
    )
    assert events, "expected runtime.privilege_drop_failed audit"
    detail = json.loads(events[-1].detail_json or "{}")
    assert detail.get("stage") == "setuid"
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    assert record.state in {IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.STOPPED}
    cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_forced_setgid_failure_fail_closed(pre_drop_probe_package):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(
        session,
        settings,
        session_factory,
        extra_env={"EMIC_SANDBOX_FORCE_DROP_FAIL": "setgid"},
    )
    assert not result.ok
    await session.commit()
    repo = IsolatedRuntimeRepository(session)
    events = await repo.list_events(
        runtime_instance_id=result.runtime_instance_id,
        event_type=RuntimeEventType.PRIVILEGE_DROP_FAILED,
    )
    assert events
    detail = json.loads(events[-1].detail_json or "{}")
    assert detail.get("stage") == "setgid"
    cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_supplementary_groups_safe(pre_drop_probe_package):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(session, settings, session_factory)
    assert result.ok
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    try:
        probes = read_probes(Path(record.data_path))
        groups = {int(x) for x in probes.get("groups", "").split(",") if x}
        assert 0 not in groups
        assert all(g >= 10001 for g in groups), f"unexpected privileged groups: {groups}"
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="pre-drop probes require Linux bwrap")
@pytest.mark.asyncio
async def test_privilege_regain_denied(pre_drop_probe_package):
    session, settings, session_factory = pre_drop_probe_package
    manager, result = await _start_pre_drop(session, settings, session_factory)
    assert result.ok
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    try:
        probes = read_probes(Path(record.data_path))
        assert probes["setuid0"].startswith("denied")
        assert probes["setgid0"].startswith("denied")
    finally:
        await manager.stop_runtime(result.runtime_instance_id)
        cleanup_sandbox_env()
