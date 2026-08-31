"""Charging signal providers built on ChargerAdapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.chargers.framework.models import ChargerAdapter, NormalizedChargerStatus
from energy_core.db.models import VehicleStateLatestModel


@dataclass(frozen=True, slots=True)
class ChargingProviderSnapshot:
    is_plugged_in: bool | None
    is_charging: bool | None
    charging_power_kw: float | None
    cumulative_energy_kwh: float | None
    recorded_at: datetime
    source: str


class MercedesChargeProvider:
    """Vehicle-side charging signals from Mercedes telemetry."""

    def snapshot_from_state(self, latest: VehicleStateLatestModel | None) -> ChargingProviderSnapshot:
        now = datetime.now(UTC)
        if latest is None:
            return ChargingProviderSnapshot(
                is_plugged_in=None,
                is_charging=None,
                charging_power_kw=None,
                cumulative_energy_kwh=None,
                recorded_at=now,
                source="MERCEDES",
            )
        recorded = latest.last_vehicle_update or now
        return ChargingProviderSnapshot(
            is_plugged_in=latest.is_plugged_in,
            is_charging=latest.is_charging,
            charging_power_kw=latest.charging_power_kw,
            cumulative_energy_kwh=None,
            recorded_at=recorded,
            source="MERCEDES",
        )


class ManualChargingProvider:
    """Placeholder provider for manually entered charging sessions."""

    def snapshot(
        self,
        *,
        is_plugged_in: bool | None = None,
        is_charging: bool | None = None,
        charging_power_kw: float | None = None,
    ) -> ChargingProviderSnapshot:
        return ChargingProviderSnapshot(
            is_plugged_in=is_plugged_in,
            is_charging=is_charging,
            charging_power_kw=charging_power_kw,
            cumulative_energy_kwh=None,
            recorded_at=datetime.now(UTC),
            source="MANUAL",
        )


class ChargerMeterProvider:
    """Charger-side signals via the existing ChargerAdapter protocol."""

    def __init__(self, adapter: ChargerAdapter) -> None:
        self._adapter = adapter

    async def snapshot(self) -> ChargingProviderSnapshot:
        now = datetime.now(UTC)
        status: NormalizedChargerStatus = await self._adapter.get_status()
        power_kw = await self._adapter.get_power()
        energy_kwh = await self._adapter.get_energy()
        is_charging = status.state == "CHARGING"
        is_plugged = status.state in {"CONNECTED", "CHARGING", "PAUSED"}
        return ChargingProviderSnapshot(
            is_plugged_in=is_plugged,
            is_charging=is_charging,
            charging_power_kw=power_kw / 1000.0 if power_kw is not None else None,
            cumulative_energy_kwh=energy_kwh,
            recorded_at=now,
            source="CHARGER",
        )
