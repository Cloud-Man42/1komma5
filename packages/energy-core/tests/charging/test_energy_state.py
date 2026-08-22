"""Tests for energy state builder and discovery."""

from datetime import UTC, datetime, timedelta

from energy_core.energy.builder import build_energy_state
from energy_core.heartbeat.field_discovery import discover_relevant_fields


def test_build_energy_state_from_live_overview():
    now = datetime.now(UTC)
    start = now - timedelta(minutes=5)
    end = now + timedelta(hours=1)
    state = build_energy_state(
        live_overview={
            "timestamp": now.isoformat().replace("+00:00", "Z"),
            "summaryCards": {
                "photovoltaic": {"production": {"value": 3200}},
                "grid": {"value": 400},
                "battery": {"power": {"value": -800}, "stateOfCharge": 65},
                "household": {"power": {"value": 2100}},
                "evChargers": [{"power": {"value": 3500}}],
            },
        },
        ev={
            "chargeSettings": {
                "chargingMode": "SMART_CHARGE",
                "targetSoc": 0.8,
                "primaryScheduleDepartureTime": "07:30",
            }
        },
        ems={"activeChargingMode": "SMART_CHARGE"},
        optimizations=[
            {
                "type": "EV_CHARGE_FROM_GRID",
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
        ],
        market_prices={"data": [{"timestamp": now.isoformat(), "price": 0.12}]},
        now=now,
    )
    assert state.pv_power_w == 3200
    assert state.ev_actual_power_w == 3500
    assert state.heartbeat_charging_mode == "SMART_CHARGE"
    assert state.ev_charge_from_grid_recommended is True
    assert state.electricity_price_eur_kwh == 0.12


def test_discovery_skips_sensitive_fields():
    hints = discover_relevant_fields(
        {
            "evChargers": [{"powerTarget": 5500}],
            "token": "secret",
            "contactEmail": "user@example.com",
        }
    )
    joined = " ".join(hints)
    assert "powerTarget" in joined
    assert "secret" not in joined
    assert "contactEmail" not in joined


def test_extract_target_from_payload():
    state = build_energy_state(
        live_overview={"powerTarget": 7200, "timestamp": datetime.now(UTC).isoformat()},
    )
    assert state.ev_target_power_w == 7200
