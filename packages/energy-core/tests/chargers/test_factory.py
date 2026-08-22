"""ChargerAdapterFactory tests."""

from types import SimpleNamespace

from energy_core.chargers.framework.adapters.charge_amps import ChargeAmpsFrameworkAdapter
from energy_core.chargers.framework.adapters.unsupported import UnsupportedChargerAdapter
from energy_core.chargers.framework.catalog import CHARGE_AMPS_CLOUD
from energy_core.chargers.framework.factory import ChargerAdapterFactory, configuration_from_model


def test_configuration_from_legacy_charge_amps():
    charger = SimpleNamespace(
        id=1,
        site_id=2,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        manufacturer_id=None,
        model_id=None,
        integration_method=None,
        chargeamp_charger_id="mock-halo",
        external_charger_id=None,
        chargeamps_api_key="",
        connection_settings=None,
        bridge_enabled=True,
        min_current_a=6.0,
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    config = configuration_from_model(charger)
    assert config.manufacturer_id == "charge-amps"
    assert config.model_id == "halo"
    assert config.integration_method == CHARGE_AMPS_CLOUD
    assert config.external_charger_id == "mock-halo"


def test_factory_returns_charge_amps_adapter_for_halo():
    charger = SimpleNamespace(
        id=1,
        site_id=2,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        manufacturer_id="charge-amps",
        model_id="halo",
        integration_method=CHARGE_AMPS_CLOUD,
        chargeamp_charger_id="mock-halo",
        external_charger_id=None,
        chargeamps_api_key="",
        connection_settings=None,
        bridge_enabled=True,
        min_current_a=6.0,
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    adapter = ChargerAdapterFactory.from_charger_model(charger)
    assert isinstance(adapter, ChargeAmpsFrameworkAdapter)


def test_factory_returns_unsupported_for_zaptec():
    charger = SimpleNamespace(
        id=1,
        site_id=2,
        name="Zaptec Go",
        manufacturer="Zaptec",
        model="Go",
        control_source="zaptec_rest",
        manufacturer_id="zaptec",
        model_id="go",
        integration_method="ZAPTEC_REST",
        chargeamp_charger_id=None,
        external_charger_id="installation-1",
        chargeamps_api_key="",
        connection_settings=None,
        bridge_enabled=False,
        min_current_a=6.0,
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    adapter = ChargerAdapterFactory.from_charger_model(charger)
    assert isinstance(adapter, UnsupportedChargerAdapter)
