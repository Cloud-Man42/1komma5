"""Shared helpers for Linux isolation E2E tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.types import RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages


async def start_runtime_with_mode(
    session,
    settings,
    session_factory,
    *,
    module_id: str = "integration.sandbox-demo",
    mode: str,
    site_id: int = 1,
    sandbox: str = "bwrap",
) -> tuple[IsolatedModuleRuntimeManager, str, Path]:
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    os.environ["EMIC_SANDBOX_MODE"] = mode
    settings = settings.model_copy(update={"isolated_runtime_sandbox": sandbox})
    manager = IsolatedModuleRuntimeManager(session, settings)
    result = await manager.start_runtime(RuntimeStartRequest(module_id=module_id, site_id=site_id))
    assert result.ok, result.message
    record = await manager.get_runtime(result.runtime_instance_id)
    assert record is not None
    data_path = Path(record.data_path or settings.resolved_isolated_runtime_data_root())
    return manager, result.runtime_instance_id, data_path


def read_probes(data_root: Path) -> dict[str, str]:
    probe_path = data_root / "probes.json"
    if not probe_path.exists():
        for candidate in data_root.rglob("probes.json"):
            probe_path = candidate
            break
    assert probe_path.exists(), f"probes.json missing under {data_root}"
    return json.loads(probe_path.read_text(encoding="utf-8"))


def cleanup_sandbox_env() -> None:
    for key in (
        "EMIC_SANDBOX_MODE",
        "EMIC_SANDBOX_FORCE_DROP_FAIL",
        "EMIC_HEARTBEAT_INTERVAL",
        "EMIC_SANDBOX_SKIP_HEARTBEAT",
        "EMIC_PROBE_ROOT_READ_CANARY",
        "EMIC_PROBE_ROOT_WRITE_CANARY",
        "EMIC_BROKER_ALLOW_URL",
        "EMIC_BROKER_OWN_SECRET",
        "EMIC_SENSIBO_FIXTURE_PODS",
    ):
        os.environ.pop(key, None)
