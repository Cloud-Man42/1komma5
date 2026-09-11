"""Step 3.5 architecture guards against vendor coupling regressions."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ENERGY_CORE_SRC = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core"


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_vehicle_command_service_is_vendor_free() -> None:
    path = ENERGY_CORE_SRC / "vehicles" / "commands" / "service.py"
    imports = _module_imports(path)
    forbidden = [
        name
        for name in imports
        if name.startswith("energy_core.vehicles.mercedes")
        or name.startswith("energy_core.integrations.mercedes")
        or "build_mercedes_provider" in name
    ]
    assert not forbidden, f"Vehicle command service must stay vendor-free: {forbidden}"


def test_charging_reasoning_has_no_heartbeat_client_import() -> None:
    path = ENERGY_CORE_SRC / "charging" / "reasoning.py"
    imports = _module_imports(path)
    forbidden = [
        name
        for name in imports
        if name.startswith("energy_core.energy.client_access")
        or name.startswith("energy_core.heartbeat")
        or name.startswith("energy_core.integrations.heartbeat")
    ]
    assert not forbidden, f"Charging reasoning must not open Heartbeat directly: {forbidden}"


def test_distributed_runtime_resolver_supports_unknown() -> None:
    path = ENERGY_CORE_SRC / "cache" / "module_runtime_state.py"
    source = path.read_text(encoding="utf-8")
    assert "distributed_runtime_expected" in source
    assert "RuntimeStatus.UNKNOWN" in source
