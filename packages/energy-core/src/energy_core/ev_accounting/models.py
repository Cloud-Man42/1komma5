"""Domain models for EV energy accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EnergyAttribution:
    solar_direct_kwh: float = 0.0
    solar_battery_kwh: float = 0.0
    grid_battery_kwh: float = 0.0
    grid_direct_kwh: float = 0.0

    @property
    def total_kwh(self) -> float:
        return (
            self.solar_direct_kwh
            + self.solar_battery_kwh
            + self.grid_battery_kwh
            + self.grid_direct_kwh
        )

    @property
    def renewable_kwh(self) -> float:
        return self.solar_direct_kwh + self.solar_battery_kwh

    @property
    def grid_kwh(self) -> float:
        return self.grid_battery_kwh + self.grid_direct_kwh


@dataclass(frozen=True, slots=True)
class AttributionResult:
    attribution: EnergyAttribution
    confidence: float
    data_quality: str


@dataclass(frozen=True, slots=True)
class SiteEnergySample:
    """Site energy snapshot for one interval."""

    pv_power_w: float
    house_consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_charge_w: float
    battery_discharge_w: float
    ev_power_w: float
    electricity_price_sek_kwh: float | None
    duration_hours: float

    @property
    def pv_kwh(self) -> float:
        return max(0.0, self.pv_power_w) * self.duration_hours / 1000.0

    @property
    def house_kwh(self) -> float:
        return max(0.0, self.house_consumption_w) * self.duration_hours / 1000.0

    @property
    def grid_import_kwh(self) -> float:
        return max(0.0, self.grid_import_w) * self.duration_hours / 1000.0

    @property
    def grid_export_kwh(self) -> float:
        return max(0.0, self.grid_export_w) * self.duration_hours / 1000.0

    @property
    def battery_charge_kwh(self) -> float:
        return max(0.0, self.battery_charge_w) * self.duration_hours / 1000.0

    @property
    def battery_discharge_kwh(self) -> float:
        return max(0.0, self.battery_discharge_w) * self.duration_hours / 1000.0


@dataclass(frozen=True, slots=True)
class BatteryLedgerState:
    solar_energy_kwh: float = 0.0
    grid_energy_kwh: float = 0.0
    grid_energy_cost_sek: float = 0.0

    @property
    def total_kwh(self) -> float:
        return self.solar_energy_kwh + self.grid_energy_kwh

    @property
    def grid_avg_cost_sek_kwh(self) -> float | None:
        if self.grid_energy_kwh <= 0:
            return None
        return self.grid_energy_cost_sek / self.grid_energy_kwh


@dataclass(frozen=True, slots=True)
class BatteryDischargeSplit:
    solar_kwh: float
    grid_kwh: float
    grid_cost_sek: float


@dataclass(frozen=True, slots=True)
class IntervalCostResult:
    actual_cash_cost_sek: float
    opportunity_cost_sek: float
    reference_cost_sek: float
    savings_sek: float | None


@dataclass(frozen=True, slots=True)
class SessionTotals:
    total_energy_kwh: float
    attribution: EnergyAttribution
    actual_cost_sek: float
    opportunity_cost_sek: float
    reference_cost_sek: float | None
    savings_sek: float | None
    smart_charging_savings_sek: float | None
    solar_contribution_sek: float
    renewable_share_pct: float
    grid_share_pct: float
    energy_quality: str
    cost_quality: str
    attribution_quality: str


@dataclass
class ChargerSessionState:
    """In-memory session tracking per charger."""

    last_vehicle_connected: bool | None = None
    last_meter_kwh: float | None = None
    last_sample_at: datetime | None = None
