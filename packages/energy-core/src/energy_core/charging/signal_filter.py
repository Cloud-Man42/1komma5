"""EWMA filtering for Heartbeat energy signals used by smart charging."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.energy.state import EnergyState


@dataclass
class FilteredEnergySignals:
    grid_import_w: float
    grid_export_w: float
    pv_power_w: float
    home_consumption_w: float
    battery_charge_power_w: float
    battery_discharge_power_w: float


@dataclass
class EnergySignalFilter:
    """Dual-speed EWMA: fast for telemetry, slow for control decisions."""

    fast_alpha: float = 0.35
    slow_alpha: float = 0.12
    fast: FilteredEnergySignals | None = None
    slow: FilteredEnergySignals | None = None

    def update(self, state: EnergyState) -> tuple[FilteredEnergySignals, FilteredEnergySignals]:
        raw = _raw_signals(state)
        if self.fast is None:
            self.fast = raw
            self.slow = raw
            return self.fast, self.slow
        assert self.slow is not None
        self.fast = _blend(self.fast, raw, self.fast_alpha)
        self.slow = _blend(self.slow, raw, self.slow_alpha)
        return self.fast, self.slow


def _raw_signals(state: EnergyState) -> FilteredEnergySignals:
    battery_charge = state.battery_charge_power_w
    if battery_charge is None and state.battery_power_w is not None:
        battery_charge = max(0.0, state.battery_power_w)
    battery_discharge = state.battery_discharge_power_w
    if battery_discharge is None and state.battery_power_w is not None:
        battery_discharge = max(0.0, -state.battery_power_w)
    return FilteredEnergySignals(
        grid_import_w=state.grid_import_w or 0.0,
        grid_export_w=state.grid_export_w or 0.0,
        pv_power_w=state.pv_power_w or 0.0,
        home_consumption_w=state.home_consumption_w or 0.0,
        battery_charge_power_w=battery_charge or 0.0,
        battery_discharge_power_w=battery_discharge or 0.0,
    )


def _blend(
    previous: FilteredEnergySignals, current: FilteredEnergySignals, alpha: float
) -> FilteredEnergySignals:
    return FilteredEnergySignals(
        grid_import_w=_ewma(previous.grid_import_w, current.grid_import_w, alpha),
        grid_export_w=_ewma(previous.grid_export_w, current.grid_export_w, alpha),
        pv_power_w=_ewma(previous.pv_power_w, current.pv_power_w, alpha),
        home_consumption_w=_ewma(previous.home_consumption_w, current.home_consumption_w, alpha),
        battery_charge_power_w=_ewma(
            previous.battery_charge_power_w, current.battery_charge_power_w, alpha
        ),
        battery_discharge_power_w=_ewma(
            previous.battery_discharge_power_w, current.battery_discharge_power_w, alpha
        ),
    )


def _ewma(previous: float, current: float, alpha: float) -> float:
    return previous + alpha * (current - previous)
