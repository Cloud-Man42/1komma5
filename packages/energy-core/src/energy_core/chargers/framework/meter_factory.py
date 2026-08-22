"""Vendor-neutral meter reader factory."""

from __future__ import annotations

import os

from energy_core.chargers.framework.catalog import CHARGE_AMPS_CLOUD
from energy_core.chargers.framework.factory import configuration_from_model
from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter
from energy_core.db.models import EvChargerModel


class MeterReaderFactory:
    @staticmethod
    def from_charger_model(charger: EvChargerModel):
        config = configuration_from_model(charger)
        if config.integration_method != CHARGE_AMPS_CLOUD:
            return None
        charger_id = config.external_charger_id
        if not charger_id:
            return None
        use_mock = os.getenv("CHARGEAMPS_MOCK", "true").lower() in {"1", "true", "yes"}
        if use_mock and not config.api_key:
            return None
        return ChargeAmpsMeterAdapter.build(
            charger_id,
            api_key=config.api_key or "",
            phases=config.phases,
            nominal_voltage_v=config.nominal_voltage_v,
        )
