"""Architecture layering tests with shrinking baseline allowlist."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
ENERGY_CORE_SRC = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core"
BACKEND_SRC = REPO_ROOT / "backend"
COLLECTOR_SRC = REPO_ROOT / "collector"

FORBIDDEN_IN_CONTRACTS = (
    "energy_core.db",
    "energy_core.integrations",
    "energy_core.chargers.charge_amps",
    "energy_core.vehicles.mercedes",
)

VENDOR_TOKENS_IN_PLATFORM = (
    "chargeamps",
    "charge_amps",
    "charge-amps",
    "mercedes",
    "arctic",
    "heartbeat",
    "sungrow",
    "zaptec",
)

# Known pre-existing violations documented in Step 1 analysis.
# This list must shrink over time — new entries fail CI.
BASELINE_MERcedes_IMPORTS_OUTSIDE_VENDOR: frozenset[str] = frozenset()

# Legacy Charge Amps imports outside vendor integration/charger layers.
LEGACY_CHARGEAMPS_PREFIXES = (
    "energy_core.chargers.charge_amps",
    "energy_core.chargers.chargeamps_config",
    "energy_core.chargers.charge_amps_web",
    "energy_core.chargers.meter_adapter",
)


BASELINE_CHARGEAMPS_IMPORTS_OUTSIDE_VENDOR: frozenset[str] = frozenset()

HEARTBEAT_LEGACY_SHIM_FILES: frozenset[str] = frozenset(
    {
        "packages/energy-core/src/energy_core/sungrow/heartbeat_provider.py",
    }
)

BASELINE_HEARTBEAT_IMPORTS_OUTSIDE_INTEGRATION: frozenset[str] = frozenset()

ARCTIC_SPA_FACADE_PREFIXES = (
    "energy_core.integrations.arctic_spa.factory",
    "energy_core.integrations.arctic_spa.errors",
    "energy_core.integrations.arctic_spa.status",
    "energy_core.integrations.arctic_spa.profiles",
    "energy_core.integrations.arctic_spa.operational",
    "energy_core.integrations.arctic_spa.polling",
)

BASELINE_ARCTIC_SPA_IMPORTS_OUTSIDE_INTEGRATION: frozenset[str] = frozenset()

BASELINE_SOLAR_INTELLIGENCE_IMPORTS_IN_BACKEND: frozenset[str] = frozenset()


def _repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _iter_python_files(package_root: Path) -> list[Path]:
    return sorted(
        path
        for path in package_root.rglob("*.py")
        if path.is_file() and "/tests/" not in str(path).replace("\\", "/")
    )


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


def _find_mercedes_imports_outside_vendor() -> set[str]:
    violations: set[str] = set()
    for path in _iter_python_files(BACKEND_SRC):
        rel = _repo_relative(path)
        imports = _module_imports(path)
        if any(name.startswith("energy_core.vehicles.mercedes") for name in imports):
            violations.add(rel)
    for path in _iter_python_files(ENERGY_CORE_SRC):
        rel = _repo_relative(path)
        if "/vehicles/mercedes/" in rel.replace("\\", "/"):
            continue
        if "/integrations/mercedes/" in rel.replace("\\", "/"):
            continue
        imports = _module_imports(path)
        if any(name.startswith("energy_core.vehicles.mercedes") for name in imports):
            violations.add(rel)
    return violations


def _is_legacy_chargeamps_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in LEGACY_CHARGEAMPS_PREFIXES
    )


def _find_legacy_chargeamps_imports_outside_vendor() -> set[str]:
    violations: set[str] = set()
    roots = [BACKEND_SRC, ENERGY_CORE_SRC, COLLECTOR_SRC]
    for root in roots:
        if not root.exists():
            continue
        for path in _iter_python_files(root):
            rel = _repo_relative(path)
            normalized = rel.replace("\\", "/")
            if "/chargers/" in normalized or "/integrations/chargeamps/" in normalized:
                continue
            imports = _module_imports(path)
            if any(_is_legacy_chargeamps_import(name) for name in imports):
                violations.add(rel)
    return violations


def _is_heartbeat_vendor_path(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    if "/integrations/heartbeat/" in normalized:
        return True
    if "/energy_core/heartbeat/" in normalized:
        return True
    return normalized in HEARTBEAT_LEGACY_SHIM_FILES


def _is_legacy_heartbeat_import(module_name: str) -> bool:
    if module_name in {
        "energy_core.heartbeat_auth",
        "energy_core.heartbeat_config",
        "energy_core.heartbeat_connection",
        "energy_core.heartbeat_client_factory",
        "energy_core.heartbeat_client",
    }:
        return True
    return module_name.startswith("energy_core.heartbeat.")


def _find_heartbeat_imports_outside_integration() -> set[str]:
    violations: set[str] = set()
    roots = [BACKEND_SRC, ENERGY_CORE_SRC, COLLECTOR_SRC]
    for root in roots:
        if not root.exists():
            continue
        for path in _iter_python_files(root):
            rel = _repo_relative(path)
            if _is_heartbeat_vendor_path(rel):
                continue
            imports = _module_imports(path)
            if any(_is_legacy_heartbeat_import(name) for name in imports):
                violations.add(rel)
    return violations


def _is_allowed_arctic_spa_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in ARCTIC_SPA_FACADE_PREFIXES
    )


def _find_arctic_spa_imports_outside_integration() -> set[str]:
    violations: set[str] = set()
    roots = [BACKEND_SRC, ENERGY_CORE_SRC, COLLECTOR_SRC]
    for root in roots:
        if not root.exists():
            continue
        for path in _iter_python_files(root):
            rel = _repo_relative(path)
            if "/integrations/arctic_spa/" in rel.replace("\\", "/"):
                continue
            imports = _module_imports(path)
            if any(
                name.startswith("energy_core.integrations.arctic_spa")
                and not _is_allowed_arctic_spa_import(name)
                for name in imports
            ):
                violations.add(rel)
    return violations


def _find_solar_intelligence_imports_in_backend() -> set[str]:
    violations: set[str] = set()
    if not BACKEND_SRC.exists():
        return violations
    for path in _iter_python_files(BACKEND_SRC):
        rel = _repo_relative(path)
        imports = _module_imports(path)
        if any(name.startswith("energy_core.solar_intelligence") for name in imports):
            violations.add(rel)
    return violations


def test_contracts_have_no_downward_dependencies() -> None:
    contracts_root = ENERGY_CORE_SRC / "contracts"
    for path in _iter_python_files(contracts_root):
        imports = _module_imports(path)
        for forbidden in FORBIDDEN_IN_CONTRACTS:
            offenders = [name for name in imports if name == forbidden or name.startswith(f"{forbidden}.")]
            assert not offenders, f"{path.name} imports forbidden modules: {offenders}"


def test_platform_has_no_vendor_imports() -> None:
    platform_root = ENERGY_CORE_SRC / "platform"
    for path in _iter_python_files(platform_root):
        imports = _module_imports(path)
        for name in imports:
            lowered = name.lower()
            assert not any(token in lowered for token in VENDOR_TOKENS_IN_PLATFORM), (
                f"{_repo_relative(path)} imports vendor module {name}"
            )


def test_mercedes_import_baseline_does_not_grow() -> None:
    current = _find_mercedes_imports_outside_vendor()
    new_violations = current - BASELINE_MERcedes_IMPORTS_OUTSIDE_VENDOR
    assert not new_violations, (
        "New Mercedes imports outside vehicles/mercedes/ detected:\n"
        + "\n".join(sorted(new_violations))
        + "\nFix the import or update the shrinking baseline allowlist."
    )
    assert current == BASELINE_MERcedes_IMPORTS_OUTSIDE_VENDOR


def test_chargeamps_import_baseline_does_not_grow() -> None:
    current = _find_legacy_chargeamps_imports_outside_vendor()
    new_violations = current - BASELINE_CHARGEAMPS_IMPORTS_OUTSIDE_VENDOR
    assert not new_violations, (
        "New legacy Charge Amps imports outside integrations/chargeamps/ detected:\n"
        + "\n".join(sorted(new_violations))
        + "\nRoute through integrations.chargeamps or contracts, or update the shrinking baseline allowlist."
    )


def test_heartbeat_import_baseline_does_not_grow() -> None:
    current = _find_heartbeat_imports_outside_integration()
    new_violations = current - BASELINE_HEARTBEAT_IMPORTS_OUTSIDE_INTEGRATION
    assert not new_violations, (
        "New Heartbeat imports outside integrations/heartbeat/ detected:\n"
        + "\n".join(sorted(new_violations))
        + "\nRoute through integrations.heartbeat or update the shrinking baseline allowlist."
    )
    assert current == BASELINE_HEARTBEAT_IMPORTS_OUTSIDE_INTEGRATION


def test_arctic_spa_import_baseline_does_not_grow() -> None:
    current = _find_arctic_spa_imports_outside_integration()
    new_violations = current - BASELINE_ARCTIC_SPA_IMPORTS_OUTSIDE_INTEGRATION
    assert not new_violations, (
        "New Arctic Spa imports outside integrations/arctic_spa/ facades detected:\n"
        + "\n".join(sorted(new_violations))
        + "\nRoute through integrations.arctic_spa factory/facades or update the shrinking baseline allowlist."
    )
    assert current == BASELINE_ARCTIC_SPA_IMPORTS_OUTSIDE_INTEGRATION


def test_solar_intelligence_backend_import_baseline_does_not_grow() -> None:
    current = _find_solar_intelligence_imports_in_backend()
    new_violations = current - BASELINE_SOLAR_INTELLIGENCE_IMPORTS_IN_BACKEND
    assert not new_violations, (
        "New solar_intelligence imports in backend detected:\n"
        + "\n".join(sorted(new_violations))
        + "\nRoute through platform.forecasting or update the shrinking baseline allowlist."
    )
    assert current == BASELINE_SOLAR_INTELLIGENCE_IMPORTS_IN_BACKEND


@pytest.mark.parametrize(
    "path_suffix",
    [
        "contracts/telemetry.py",
        "contracts/health.py",
        "contracts/capabilities.py",
        "platform/events/bus.py",
        "platform/devices/registry.py",
    ],
)
def test_new_layer_modules_exist(path_suffix: str) -> None:
    assert (ENERGY_CORE_SRC / path_suffix).is_file()
