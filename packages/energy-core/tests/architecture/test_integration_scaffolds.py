"""Architecture tests for new integration packages."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
INTEGRATIONS = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "integrations"


def test_zaptec_and_tesla_packages_exist() -> None:
    assert (INTEGRATIONS / "zaptec" / "factory.py").exists()
    assert (INTEGRATIONS / "tesla" / "factory.py").exists()


def test_charger_factory_registers_zaptec_without_vendor_leak() -> None:
    from energy_core.chargers.framework.factory import _INTEGRATION_BUILDERS
    from energy_core.chargers.framework.catalog import ZAPTEC_REST

    builder = _INTEGRATION_BUILDERS[ZAPTEC_REST]
    assert "zaptec" in builder.__module__


def test_vehicle_factory_registers_tesla() -> None:
    from energy_core.vehicles.provider_factory import _PROVIDER_REGISTRY

    assert "tesla" in _PROVIDER_REGISTRY
