"""Charge Amps integration tests."""

from energy_core.integrations.chargeamps.config import build_chargeamps_connection_info
from energy_core.integrations.chargeamps.meter_adapter import ChargeAmpsMeterAdapter


def test_config_reexport_matches_integration(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.setenv("CHARGEAMPS_API_KEY", "test-key")
    info = build_chargeamps_connection_info()
    assert info.ready is True
    assert info.api_key_configured is True


def test_meter_adapter_builds_from_integration_package():
    adapter = ChargeAmpsMeterAdapter.build("test-charger", api_key="key")
    assert adapter.charger_id == "test-charger"


def test_chargeamps_legacy_shims_reexport_integration():
    from energy_core.chargers import charge_amps as legacy
    from energy_core.chargers import charge_amps_web as legacy_web
    from energy_core.integrations.chargeamps import controller as canonical
    from energy_core.integrations.chargeamps import web_controller as canonical_web

    assert legacy.build_chargeamps_controller is canonical.build_chargeamps_controller
    assert legacy_web.ChargeAmpsWebController is canonical_web.ChargeAmpsWebController
