"""Charge Amps control facade — canonical import path for Halo controllers."""

from __future__ import annotations

from energy_core.chargers.charge_amps import (
    CHARGEAMPS_API_BASE,
    DEFAULT_CONNECTOR_ID,
    ChargeAmpsController,
    ChargeAmpsExternalController,
    ChargeAmpsHaloController,
    build_chargeamps_controller,
)
from energy_core.chargers.mock import MockChargeAmpsController

__all__ = [
    "CHARGEAMPS_API_BASE",
    "DEFAULT_CONNECTOR_ID",
    "ChargeAmpsController",
    "ChargeAmpsExternalController",
    "ChargeAmpsHaloController",
    "MockChargeAmpsController",
    "build_chargeamps_controller",
]
