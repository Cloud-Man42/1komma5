"""Vendor-neutral meter reader factory (delegates to Charge Amps integration)."""

from __future__ import annotations

from energy_core.contracts.devices.meter import IMeterReader
from energy_core.db.models import EvChargerModel


class MeterReaderFactory:
    @staticmethod
    def from_charger_model(charger: EvChargerModel) -> IMeterReader | None:
        from energy_core.integrations.chargeamps.meter_factory import meter_reader_for_charger

        return meter_reader_for_charger(charger)
