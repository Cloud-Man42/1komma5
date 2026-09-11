"""Tests for module dependency resolver."""

import pytest

from energy_core.platform.capabilities import Capability, CapabilityRegistry
from energy_core.platform.modules.registry import ModuleDescriptor, ModuleRegistry
from energy_core.platform.modules.resolver import ModuleDependencyResolver
from energy_core.platform.modules.types import ModuleType


def _registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(
        ModuleDescriptor(
            module_id="integration.chargeamps",
            name="Charge Amps",
            version="1.0.0",
            module_type=ModuleType.INTEGRATION,
            capabilities_provided=(Capability.EV_CHARGER_START, Capability.EV_CHARGER_STOP),
        )
    )
    registry.register(
        ModuleDescriptor(
            module_id="feature.smart-charging",
            name="Smart Charging",
            version="1.0.0",
            module_type=ModuleType.FEATURE,
            dependencies=("integration.chargeamps",),
            capabilities_required=(Capability.EV_CHARGER_START, Capability.EV_CHARGER_STOP),
            optional_capabilities=(Capability.VEHICLE_READ_SOC,),
        )
    )
    return registry


def test_startup_order_respects_dependencies() -> None:
    resolver = ModuleDependencyResolver(_registry())
    order = resolver.startup_order(("feature.smart-charging", "integration.chargeamps"))
    assert order.index("integration.chargeamps") < order.index("feature.smart-charging")


def test_startup_order_detects_cycles() -> None:
    registry = ModuleRegistry()
    registry.register(ModuleDescriptor(module_id="a", name="A", version="1", dependencies=("b",)))
    registry.register(ModuleDescriptor(module_id="b", name="B", version="1", dependencies=("a",)))
    resolver = ModuleDependencyResolver(registry)
    with pytest.raises(ValueError, match="Circular"):
        resolver.startup_order(("a", "b"))


def test_can_start_missing_required_capabilities() -> None:
    registry = _registry()
    caps = CapabilityRegistry()
    resolver = ModuleDependencyResolver(registry, caps)
    result = resolver.can_start(
        "feature.smart-charging",
        site_id=1,
        enabled_modules={"feature.smart-charging"},
        capability_registry=caps,
    )
    assert result.can_start is False
    assert Capability.EV_CHARGER_START in result.missing_required


def test_can_start_when_capabilities_present() -> None:
    registry = _registry()
    caps = CapabilityRegistry()
    caps.register_provider(site_id=1, module_id="integration.chargeamps", capability=Capability.EV_CHARGER_START)
    caps.register_provider(site_id=1, module_id="integration.chargeamps", capability=Capability.EV_CHARGER_STOP)
    resolver = ModuleDependencyResolver(registry, caps)
    result = resolver.can_start(
        "feature.smart-charging",
        site_id=1,
        enabled_modules={"feature.smart-charging", "integration.chargeamps"},
        capability_registry=caps,
    )
    assert result.can_start is True
    assert Capability.VEHICLE_READ_SOC in result.missing_optional


def test_can_disable_blocks_dependent_modules() -> None:
    registry = _registry()
    caps = CapabilityRegistry()
    caps.register_provider(site_id=1, module_id="integration.chargeamps", capability=Capability.EV_CHARGER_START)
    caps.register_provider(site_id=1, module_id="integration.chargeamps", capability=Capability.EV_CHARGER_STOP)
    resolver = ModuleDependencyResolver(registry, caps)
    result = resolver.can_disable(
        "integration.chargeamps",
        site_id=1,
        enabled_modules={"integration.chargeamps", "feature.smart-charging"},
        capability_registry=caps,
    )
    assert result.allowed is False
    assert "feature.smart-charging" in result.dependent_modules
