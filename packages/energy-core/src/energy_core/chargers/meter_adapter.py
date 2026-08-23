"""Charge Amps meter readings for EV energy accounting."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from energy_core.chargers.charge_amps import ChargeAmpsController, build_chargeamps_controller
from energy_core.chargers.charge_amps_web import ChargeAmpsWebController
from energy_core.chargers.vehicle_status import (
    vehicle_connected_from_external_connector,
    vehicle_connected_from_web_connector,
)

logger = logging.getLogger(__name__)

DEFAULT_CONNECTOR_ID = 1
DEFAULT_NOMINAL_VOLTAGE_V = 230.0


@dataclass(frozen=True, slots=True)
class MeterSnapshot:
    """Point-in-time charger meter reading."""

    recorded_at: datetime
    cumulative_kwh: float | None
    power_w: float | None
    configured_current_a: float | None
    actual_charging_current_a: float | None
    is_charging: bool
    vehicle_connected: bool
    ocpp_status: str
    phase_current_l1_a: float | None
    phase_current_l2_a: float | None
    phase_current_l3_a: float | None
    energy_source: str  # meter | power_estimate | unavailable


class MeterReader(Protocol):
    async def get_snapshot(self) -> MeterSnapshot: ...


class ChargeAmpsMeterAdapter:
    """Read cumulative meter and power from Charge Amps web or external API."""

    def __init__(
        self,
        charger_id: str,
        *,
        connector_id: int = DEFAULT_CONNECTOR_ID,
        nominal_voltage_v: float = DEFAULT_NOMINAL_VOLTAGE_V,
        phases: int = 3,
        web_controller: ChargeAmpsWebController | None = None,
        external_client: Any | None = None,
    ) -> None:
        self.charger_id = charger_id
        self._connector_id = connector_id
        self._nominal_voltage_v = nominal_voltage_v
        self._phases = phases
        self._web = web_controller
        self._external = external_client

    @classmethod
    def from_controller(
        cls, controller: ChargeAmpsController, *, phases: int = 3
    ) -> ChargeAmpsMeterAdapter:
        if isinstance(controller, ChargeAmpsWebController):
            return cls(controller.charger_id, web_controller=controller, phases=phases)
        external = getattr(controller, "_adapter", None)
        client = getattr(external, "_client", None) if external is not None else None
        return cls(
            controller.charger_id if hasattr(controller, "charger_id") else "unknown",
            external_client=client,
            phases=phases,
        )

    @classmethod
    def build(
        cls,
        charger_id: str,
        *,
        api_key: str = "",
        email: str = "",
        password: str = "",
        phases: int = 3,
        nominal_voltage_v: float = DEFAULT_NOMINAL_VOLTAGE_V,
    ) -> ChargeAmpsMeterAdapter:
        resolved_email = email or os.getenv("CHARGEAMPS_EMAIL", "")
        resolved_password = password or os.getenv("CHARGEAMPS_PASSWORD", "")
        if resolved_email and resolved_password:
            web = ChargeAmpsWebController(
                charger_id,
                email=resolved_email,
                password=resolved_password,
                use_mock=False,
            )
            adapter = cls(charger_id, web_controller=web, phases=phases)
            adapter._nominal_voltage_v = nominal_voltage_v
            return adapter

        controller = build_chargeamps_controller(
            charger_id,
            api_key=api_key or os.getenv("CHARGEAMPS_API_KEY", ""),
            email=resolved_email,
            password=resolved_password,
            use_mock=False,
            phases=phases,
        )
        adapter = cls.from_controller(controller, phases=phases)
        adapter._nominal_voltage_v = nominal_voltage_v
        return adapter

    async def get_snapshot(self) -> MeterSnapshot:
        now = datetime.now(UTC)
        if self._web is not None:
            return await self._snapshot_from_web(now)
        if self._external is not None:
            return await self._snapshot_from_external(now)
        return MeterSnapshot(
            recorded_at=now,
            cumulative_kwh=None,
            power_w=None,
            configured_current_a=None,
            actual_charging_current_a=None,
            is_charging=False,
            vehicle_connected=False,
            ocpp_status="",
            phase_current_l1_a=None,
            phase_current_l2_a=None,
            phase_current_l3_a=None,
            energy_source="unavailable",
        )

    async def _snapshot_from_web(self, now: datetime) -> MeterSnapshot:
        data = await self._web._request("GET", f"/chargepoints/{self.charger_id}")
        connector = _connector_by_id(data.get("connectors") or [], self._connector_id) or {}
        ocpp = str(connector.get("ocppStatus") or "")
        is_charging = bool(connector.get("isCharging")) or ocpp == "Charging"
        vehicle_connected = vehicle_connected_from_web_connector(connector)

        l1 = _float_or_none(connector.get("current1"))
        l2 = _float_or_none(connector.get("current2"))
        l3 = _float_or_none(connector.get("current3"))
        charging_current = connector.get("chargingCurrent") or {}
        if isinstance(charging_current, dict):
            l1 = l1 if l1 is not None else _float_or_none(charging_current.get("current1"))
            l2 = l2 if l2 is not None else _float_or_none(charging_current.get("current2"))
            l3 = l3 if l3 is not None else _float_or_none(charging_current.get("current3"))

        cumulative = _float_or_none(connector.get("totalConsumptionKwh"))
        if cumulative is None:
            cumulative = _float_or_none(connector.get("totalConsumptionRaw"))

        configured = _float_or_none(connector.get("userCurrent"))
        if configured is None:
            configured = _float_or_none(connector.get("currentCurrent"))
        actual_current = _max_phase_current(l1, l2, l3)
        power_w = _power_from_phases(l1, l2, l3, self._nominal_voltage_v, self._phases)
        source = (
            "meter" if cumulative is not None else ("power_estimate" if power_w else "unavailable")
        )

        return MeterSnapshot(
            recorded_at=now,
            cumulative_kwh=cumulative,
            power_w=power_w,
            configured_current_a=configured,
            actual_charging_current_a=actual_current,
            is_charging=is_charging,
            vehicle_connected=vehicle_connected,
            ocpp_status=ocpp,
            phase_current_l1_a=l1,
            phase_current_l2_a=l2,
            phase_current_l3_a=l3,
            energy_source=source,
        )

    async def _snapshot_from_external(self, now: datetime) -> MeterSnapshot:
        status = await self._external.get_chargepoint_status(force=True)
        connectors = status.get("connectorStatuses") or status.get("connector_statuses") or []
        connector = _connector_by_id(connectors, self._connector_id) or {}
        ocpp = str(connector.get("status") or connector.get("ocppStatus") or "")
        is_charging = ocpp.casefold() == "charging" or bool(
            connector.get("isCharging") or connector.get("is_charging")
        )
        vehicle_connected = vehicle_connected_from_external_connector(connector)
        cumulative = _float_or_none(
            connector.get("totalConsumptionKwh") or connector.get("energyDelivered")
        )
        return MeterSnapshot(
            recorded_at=now,
            cumulative_kwh=cumulative,
            power_w=None,
            configured_current_a=None,
            actual_charging_current_a=None,
            is_charging=is_charging,
            vehicle_connected=vehicle_connected,
            ocpp_status=ocpp,
            phase_current_l1_a=None,
            phase_current_l2_a=None,
            phase_current_l3_a=None,
            energy_source="meter" if cumulative is not None else "unavailable",
        )


def session_energy_from_meter(
    start_kwh: float | None, stop_kwh: float | None
) -> tuple[float | None, str]:
    """Return (session_kwh, quality) from cumulative meter delta."""
    if start_kwh is None or stop_kwh is None:
        return None, "INCOMPLETE"
    delta = stop_kwh - start_kwh
    if delta < 0:
        return None, "INCOMPLETE"
    if delta == 0:
        return 0.0, "MEASURED"
    return round(delta, 4), "MEASURED"


def integrate_power_kwh(power_w: float, duration_hours: float) -> float:
    if power_w <= 0 or duration_hours <= 0:
        return 0.0
    return round(power_w * duration_hours / 1000.0, 4)


def _connector_by_id(connectors: list[Any], connector_id: int) -> dict[str, Any] | None:
    for connector in connectors:
        if isinstance(connector, dict) and connector.get("connectorId") == connector_id:
            return connector
    return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _max_phase_current(
    l1: float | None,
    l2: float | None,
    l3: float | None,
) -> float | None:
    values = [value for value in (l1, l2, l3) if value is not None and value > 0]
    if not values:
        return None
    return max(values)


def _power_from_phases(
    l1: float | None,
    l2: float | None,
    l3: float | None,
    voltage: float,
    phases: int,
) -> float | None:
    currents = [c for c in (l1, l2, l3) if c is not None and c > 0]
    if not currents:
        return None
    if phases >= 3 and len(currents) >= 3:
        return sum(currents) * voltage
    return sum(currents[:phases]) * voltage
