"""Read-only optimization context for future battery/horizon engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from energy_core.energy.unified import UnifiedEnergyState


@dataclass(frozen=True, slots=True)
class DeviceCapability:
    device_id: str
    device_type: str
    min_power_kw: float | None = None
    max_power_kw: float | None = None
    min_soc_percent: float | None = None
    max_soc_percent: float | None = None
    capacity_kwh: float | None = None


@dataclass(frozen=True, slots=True)
class Constraint:
    name: str
    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class EnergyOptimizationContext:
    site_id: int
    site_slug: str
    timestamp: datetime
    state: UnifiedEnergyState
    import_price_sek_kwh: float | None = None
    export_price_sek_kwh: float | None = None
    solar_forecast_kwh_today: float | None = None
    load_forecast_kw: float | None = None
    devices: tuple[DeviceCapability, ...] = ()
    constraints: tuple[Constraint, ...] = field(default_factory=tuple)


def build_optimization_context(
    state: UnifiedEnergyState,
    *,
    import_price_sek_kwh: float | None = None,
    export_price_sek_kwh: float | None = None,
    solar_forecast_kwh_today: float | None = None,
    load_forecast_kw: float | None = None,
) -> EnergyOptimizationContext:
    devices: list[DeviceCapability] = []
    if state.battery.soc_percent is not None:
        devices.append(
            DeviceCapability(
                device_id="battery",
                device_type="battery",
                min_power_kw=0.0,
                max_power_kw=state.battery.charge_kw,
                min_soc_percent=0.0,
                max_soc_percent=100.0,
                capacity_kwh=state.battery.capacity_kwh,
            )
        )
    if state.ev.connected:
        devices.append(
            DeviceCapability(
                device_id="ev",
                device_type="ev",
                max_power_kw=state.ev.power_kw,
                min_soc_percent=state.ev.soc_percent,
                max_soc_percent=state.ev.target_soc,
            )
        )
    constraints = (
        Constraint(name="grid_import_limit_kw", value=11.0, unit="kW"),
    )
    return EnergyOptimizationContext(
        site_id=state.site_id,
        site_slug=state.site_slug,
        timestamp=state.timestamp,
        state=state,
        import_price_sek_kwh=import_price_sek_kwh or state.prices.import_price_sek_kwh,
        export_price_sek_kwh=export_price_sek_kwh,
        solar_forecast_kwh_today=solar_forecast_kwh_today or state.solar.expected_today_kwh,
        load_forecast_kw=load_forecast_kw,
        devices=tuple(devices),
        constraints=constraints,
    )
