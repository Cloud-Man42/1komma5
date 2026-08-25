"""Infer power consumption from Arctic Spa status states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from energy_core.consumer_accounting.types import DataQuality, SpaEnergySample
from energy_core.integrations.arctic_spa.config import SpaPowerProfiles
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus


class SpaMeterProvider(Protocol):
    def estimate_sample(
        self,
        status: ArcticSpaStatus,
        *,
        prev_status: ArcticSpaStatus | None,
        elapsed_seconds: float,
        poll_interval_seconds: float,
    ) -> SpaEnergySample: ...


@dataclass(slots=True)
class InferredArcticSpaMeter:
    profiles: SpaPowerProfiles

    def estimate_sample(
        self,
        status: ArcticSpaStatus,
        *,
        prev_status: ArcticSpaStatus | None,
        elapsed_seconds: float,
        poll_interval_seconds: float,
    ) -> SpaEnergySample:
        if not status.connected:
            return SpaEnergySample(
                power_w=0.0,
                energy_delta_wh=0.0,
                heater_active=False,
                pump_states=status.pump_states,
                water_temperature_c=status.temperature_c,
                set_temperature_c=status.setpoint_c,
                source="ARCTIC_SPA_REST",
                quality=DataQuality.MISSING,
                component_breakdown={},
            )

        breakdown = self._component_breakdown(status)
        power_w = min(sum(breakdown.values()), self.profiles.max_plausible_power_w)
        if elapsed_seconds <= 0:
            energy_delta_wh = 0.0
            quality = DataQuality.CALCULATED
        else:
            effective_elapsed = min(elapsed_seconds, poll_interval_seconds * 2)
            quality = DataQuality.ESTIMATED if elapsed_seconds > poll_interval_seconds * 2 else DataQuality.CALCULATED
            prev_power = self._power_from_status(prev_status) if prev_status else power_w
            avg_power = (prev_power + power_w) / 2.0
            energy_delta_wh = max(0.0, avg_power * (effective_elapsed / 3600.0))

        return SpaEnergySample(
            power_w=power_w,
            energy_delta_wh=energy_delta_wh,
            heater_active=status.heater_active,
            pump_states=status.pump_states,
            water_temperature_c=status.temperature_c,
            set_temperature_c=status.setpoint_c,
            source="ARCTIC_SPA_REST",
            quality=quality,
            component_breakdown=breakdown,
        )

    def _power_from_status(self, status: ArcticSpaStatus | None) -> float:
        if status is None or not status.connected:
            return 0.0
        return min(sum(self._component_breakdown(status).values()), self.profiles.max_plausible_power_w)

    def _component_breakdown(self, status: ArcticSpaStatus) -> dict[str, float]:
        breakdown: dict[str, float] = {}
        if status.heater_active:
            breakdown["heater"] = self.profiles.heater_w
        for name, state in status.pump_states.items():
            if state == "low":
                breakdown[name] = self.profiles.pump_low_w
            elif state in {"high", "on"}:
                breakdown[name] = self.profiles.pump_high_w
        if status.filter_status == "Filtering" and "heater" not in breakdown:
            breakdown["circulation"] = self.profiles.circulation_w
        for blower in ("blower1", "blower2"):
            value = getattr(status, blower)
            if value == "on":
                breakdown[blower] = self.profiles.blower_w
        return breakdown
