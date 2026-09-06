"""Charge Amps integration package."""

from energy_core.integrations.chargeamps.config import (
    ChargeAmpsConnectionInfo,
    assert_chargeamps_production_safe,
    build_chargeamps_connection_info,
)

__all__ = [
    "ChargeAmpsConnectionInfo",
    "ChargeAmpsMeterAdapter",
    "assert_chargeamps_production_safe",
    "build_chargeamps_connection_info",
    "build_meter_reader",
    "meter_reader_for_charger",
]


def __getattr__(name: str):
    if name == "ChargeAmpsMeterAdapter":
        from energy_core.integrations.chargeamps.meter_adapter import ChargeAmpsMeterAdapter

        return ChargeAmpsMeterAdapter
    if name in {"build_meter_reader", "meter_reader_for_charger"}:
        from energy_core.integrations.chargeamps import meter_factory

        return getattr(meter_factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
