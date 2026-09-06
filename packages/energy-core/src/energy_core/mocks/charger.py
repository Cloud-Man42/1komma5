"""Vendor-neutral mock charger implementing ChargerAdapter contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.framework.models import (
    ChargerCapabilities,
    ChargingSession as FrameworkChargingSession,
    ConnectionTestResult,
    MeterValues,
    NormalizedChargerStatus,
)


@dataclass
class MockCharger:
    """Unbranded charger mock — not tied to Charge Amps."""

    charger_id: str = "mock-charger"
    connected: bool = True
    vehicle_connected: bool = False
    charging: bool = False
    current_a: float = 10.0
    power_w: float = 0.0
    energy_kwh: float = 0.0
    _capabilities: ChargerCapabilities = field(
        default_factory=lambda: ChargerCapabilities(
            supports_current_control=True,
            supports_remote_start_stop=True,
            supports_power_reading=True,
        )
    )

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def get_status(self) -> NormalizedChargerStatus:
        state = "CHARGING" if self.charging else ("CONNECTED" if self.vehicle_connected else "AVAILABLE")
        if not self.connected:
            state = "OFFLINE"
        return NormalizedChargerStatus(
            online=self.connected,
            vehicle_connected=self.vehicle_connected,
            charging=self.charging,
            state=state,
            requested_current_a=self.current_a if self.charging else None,
            actual_current_a=self.current_a if self.charging else None,
            configured_current_a=self.current_a,
            power_w=self.power_w if self.charging else 0.0,
            session_energy_kwh=self.energy_kwh,
            timestamp=datetime.now(UTC),
        )

    async def get_legacy_status(self) -> ChargerStatus:
        return ChargerStatus(
            connected=self.connected,
            vehicle_connected=self.vehicle_connected,
            current_limit_a=self.current_a,
            charging=self.charging,
        )

    async def get_capabilities(self) -> ChargerCapabilities:
        return self._capabilities

    async def start_charging(self) -> None:
        self.charging = True
        self.power_w = max(self.power_w, 2300.0)

    async def stop_charging(self) -> None:
        self.charging = False
        self.power_w = 0.0

    async def get_requested_current(self) -> float | None:
        return self.current_a

    async def get_actual_current(self) -> float | None:
        return self.current_a if self.charging else None

    async def set_max_current(self, amps: float) -> None:
        self.current_a = amps

    async def get_power(self) -> float | None:
        return self.power_w if self.charging else 0.0

    async def get_energy(self) -> float | None:
        return self.energy_kwh

    async def get_session(self) -> FrameworkChargingSession | None:
        if not self.charging:
            return None
        return FrameworkChargingSession(
            charger_id=self.charger_id,
            started_at=datetime.now(UTC),
            energy_kwh=self.energy_kwh,
        )

    async def test_connection(self) -> ConnectionTestResult:
        status = "CONNECTED" if self.connected else "UNKNOWN_ERROR"
        return ConnectionTestResult(success=self.connected, status=status, message="mock")

    async def get_meter_values(self) -> MeterValues | None:
        return None
