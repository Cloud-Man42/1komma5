"""Tests for capability registry."""

from energy_core.platform.capabilities import Capability, default_capability_registry


def setup_function() -> None:
    default_capability_registry._providers.clear()


def test_register_and_lookup_provider() -> None:
    default_capability_registry.register_provider(
        site_id=1,
        module_id="integration.chargeamps",
        capability=Capability.EV_CHARGER_START,
        device_id="ev_charger:1",
    )
    providers = default_capability_registry.providers_for(1, Capability.EV_CHARGER_START)
    assert len(providers) == 1
    assert providers[0].module_id == "integration.chargeamps"


def test_multiple_providers_same_capability() -> None:
    default_capability_registry.register_provider(
        site_id=1,
        module_id="integration.heartbeat",
        capability=Capability.ENERGY_READ_GRID_POWER,
    )
    default_capability_registry.register_provider(
        site_id=1,
        module_id="integration.sungrow",
        capability=Capability.ENERGY_READ_GRID_POWER,
    )
    providers = default_capability_registry.providers_for(1, Capability.ENERGY_READ_GRID_POWER)
    assert {item.module_id for item in providers} == {"integration.heartbeat", "integration.sungrow"}
