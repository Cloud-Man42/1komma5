"""Build IMeterReader instances for Charge Amps chargers."""

from __future__ import annotations

import os

from energy_core.contracts.devices.meter import IMeterReader
from energy_core.db.models import EvChargerModel
from energy_core.integrations.chargeamps.meter_adapter import ChargeAmpsMeterAdapter
from energy_core.secrets import CredentialCipher


def build_meter_reader(
    charger_id: str,
    *,
    api_key: str = "",
    phases: int = 3,
    nominal_voltage_v: float = 230.0,
) -> IMeterReader:
    return ChargeAmpsMeterAdapter.build(
        charger_id,
        api_key=api_key,
        phases=phases,
        nominal_voltage_v=nominal_voltage_v,
    )


def meter_reader_for_charger(charger: EvChargerModel) -> IMeterReader | None:
    """Return a meter reader for supported charger configs, else None."""
    from energy_core.chargers.framework.catalog import CHARGE_AMPS_CLOUD
    from energy_core.chargers.framework.factory import configuration_from_model

    config = configuration_from_model(charger)
    if config.integration_method != CHARGE_AMPS_CLOUD:
        return None
    charger_id = config.external_charger_id or charger.chargeamp_charger_id
    if not charger_id:
        return None
    use_mock = os.getenv("CHARGEAMPS_MOCK", "true").lower() in {"1", "true", "yes"}
    api_key = CredentialCipher().decrypt(charger.chargeamps_api_key) or os.getenv("CHARGEAMPS_API_KEY", "")
    if use_mock and not api_key:
        return None
    return build_meter_reader(
        charger_id,
        api_key=api_key or "",
        phases=config.phases,
        nominal_voltage_v=config.nominal_voltage_v,
    )
