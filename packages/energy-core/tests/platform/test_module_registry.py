"""Module registry tests."""

import pytest

from energy_core.contracts.capabilities import DeviceCapability
from energy_core.platform.modules.registry import ModuleDescriptor, ModuleRegistry


def test_register_and_list_modules() -> None:
    registry = ModuleRegistry()
    descriptor = ModuleDescriptor(
        module_id="smart_charging",
        name="Smart Charging",
        version="1.0.0",
        capabilities_provided=(DeviceCapability.SMART_CHARGING,),
    )
    registry.register(descriptor)
    assert registry.get("smart_charging") == descriptor
    assert len(registry.list_modules()) == 1


def test_duplicate_registration_raises() -> None:
    registry = ModuleRegistry()
    descriptor = ModuleDescriptor(module_id="dup", name="Dup", version="1.0.0")
    registry.register(descriptor)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(descriptor)
