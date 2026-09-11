"""Acceptance scenario for Step 2 spec section 46."""

from energy_core.platform.capabilities import Capability, CapabilityRegistry
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.registry import default_module_registry
from energy_core.platform.modules.resolver import ModuleDependencyResolver


def test_disable_chargeamps_blocks_smart_charging_capabilities() -> None:
    default_module_registry.clear()
    register_default_modules()
    registry_caps = CapabilityRegistry()
    registry_caps.register_provider(
        site_id=1,
        module_id="integration.chargeamps",
        capability=Capability.EV_CHARGER_START,
    )
    registry_caps.register_provider(
        site_id=1,
        module_id="integration.chargeamps",
        capability=Capability.EV_CHARGER_STOP,
    )

    resolver = ModuleDependencyResolver()
    enabled = {"integration.chargeamps", "feature.smart-charging"}

    ready = resolver.can_start(
        "feature.smart-charging",
        site_id=1,
        enabled_modules=enabled,
        capability_registry=registry_caps,
    )
    assert ready.can_start is True

    disable_check = resolver.can_disable(
        "integration.chargeamps",
        site_id=1,
        enabled_modules=enabled,
        capability_registry=registry_caps,
    )
    assert disable_check.allowed is False

    registry_caps.clear_site(1)
    enabled_without_ca = {"feature.smart-charging"}
    blocked = resolver.can_start(
        "feature.smart-charging",
        site_id=1,
        enabled_modules=enabled_without_ca,
        capability_registry=registry_caps,
    )
    assert blocked.can_start is False
    assert Capability.EV_CHARGER_START in blocked.missing_required
    assert Capability.EV_CHARGER_STOP in blocked.missing_required
