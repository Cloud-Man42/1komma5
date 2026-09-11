"""Extended Linux adversarial probes (Sprint C.6)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from test_adversarial_matrix import _read_probes, _start_with_mode


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_capabilities_dropped(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_caps")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes.get("caps_none") == "yes" or probes.get("CapEff") in {"0", "0000000000000000"}
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_direct_network_matrix_denied(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_network_full")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        for key, value in probes.items():
            assert value.startswith("denied"), f"{key} was {value}"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_host_proc_and_foreign_data_denied(sandbox_demo_package, tmp_path):
    session, settings, session_factory = sandbox_demo_package
    foreign = tmp_path / "other-runtime" / "secret.txt"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("secret", encoding="utf-8")
    os.environ["EMIC_PROBE_FOREIGN_DATA"] = str(foreign)
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_filesystem")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["/proc/1/environ"].startswith("denied")
        assert probes["foreign_data"].startswith("denied")
        assert probes["tmp_private"] == "allowed"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)
        os.environ.pop("EMIC_PROBE_FOREIGN_DATA", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_privilege_escalation_denied(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_privesc")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        for key, value in probes.items():
            assert not value.startswith("allowed"), f"{key} escalated: {value}"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_fork_limit_contained(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap", "isolated_runtime_max_processes": 16})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_fork")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["fork"].startswith("stopped:")
        count = int(probes["fork"].split(":")[1])
        assert count <= 16
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_fd_limit_contained(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap", "isolated_runtime_max_open_files": 64})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_fd")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["fd"].startswith("stopped:")
        count = int(probes["fd"].split(":")[1])
        assert count <= 64
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_low_privilege_uid_gid(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={
        "isolated_runtime_sandbox": "bwrap",
        "isolated_runtime_module_uid": 10001,
        "isolated_runtime_module_gid": 10001,
    })
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_uid")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["uid"] == "10001"
        assert probes["euid"] == "10001"
        assert probes["gid"] == "10001"
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_memory_limit_contained(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap", "isolated_runtime_memory_mb": 64})
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_memory")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        assert probes["memory"].startswith("stopped:")
        mb = int(probes["memory"].split(":")[1].replace("MB", ""))
        assert mb <= 64
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bwrap adversarial probes require Linux sandbox")
@pytest.mark.asyncio
async def test_rlimits_applied_in_sandbox(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={
        "isolated_runtime_sandbox": "bwrap",
        "isolated_runtime_memory_mb": 96,
        "isolated_runtime_max_processes": 12,
        "isolated_runtime_max_open_files": 48,
        "isolated_runtime_cpu_time_limit_seconds": 120,
    })
    manager, runtime_id, _ = await _start_with_mode(session, settings, session_factory, "probe_rlimits")
    try:
        probes = _read_probes(Path(settings.resolved_isolated_runtime_data_root()), "integration.sandbox-demo", 1, runtime_id)
        as_soft, _ = (int(x) for x in probes["AS"].split(":", 1))
        nproc_soft, _ = (int(x) for x in probes["NPROC"].split(":", 1))
        nofile_soft, _ = (int(x) for x in probes["NOFILE"].split(":", 1))
        cpu_soft, _ = (int(x) for x in probes["CPU"].split(":", 1))
        assert as_soft <= 96 * 1024 * 1024
        assert nproc_soft <= 12
        assert nofile_soft <= 48
        assert cpu_soft <= 120
    finally:
        await manager.stop_runtime(runtime_id)
        os.environ.pop("EMIC_SANDBOX_MODE", None)
