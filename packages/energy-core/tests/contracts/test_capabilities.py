"""Contract capability model tests."""

from energy_core.chargers.framework.models import ChargerCapabilities
from energy_core.contracts.capabilities import DeviceCapability, supports


def test_supports_maps_framework_booleans() -> None:
    caps = ChargerCapabilities(
        can_read_power=True,
        can_start_charging=True,
        can_stop_charging=False,
        can_set_max_current=True,
    )
    assert supports(caps, DeviceCapability.READ_POWER)
    assert supports(caps, DeviceCapability.START)
    assert not supports(caps, DeviceCapability.STOP)
    assert supports(caps, DeviceCapability.SET_CURRENT)


def test_supports_legacy_alias_fields() -> None:
    caps = ChargerCapabilities.from_legacy(
        min_current_a=6.0,
        max_current_a=16.0,
        phases=3,
        supports_current_control=True,
        supports_remote_start_stop=True,
        supports_power_reading=True,
        supports_dynamic_phases=False,
    )
    assert supports(caps, DeviceCapability.SET_CURRENT)
    assert supports(caps, DeviceCapability.START)
    assert supports(caps, DeviceCapability.READ_POWER)


def test_supports_unknown_capability_returns_false() -> None:
    caps = ChargerCapabilities()
    assert not supports(caps, DeviceCapability.OCPP)
