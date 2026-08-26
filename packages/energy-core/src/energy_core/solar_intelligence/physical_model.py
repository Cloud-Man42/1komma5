"""Multi-array physical PV model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy_core.solar_forecast.constants import INTERVAL_HOURS, REFERENCE_TEMP_C, TEMP_COEFFICIENT_PER_C
from energy_core.solar_intelligence.geometry import SolarGeometryService
from energy_core.solar_intelligence.poa import PoaTranspositionService
from energy_core.solar_intelligence.types import WeatherSnapshot


@dataclass(frozen=True, slots=True)
class PvArraySpec:
    name: str
    capacity_kwp: float
    tilt_deg: float
    azimuth_deg: float


class PhysicalPvModel:
    """POA → kWp → temperature → losses → inverter clip."""

    def __init__(
        self,
        *,
        arrays: list[PvArraySpec],
        system_loss_percent: float,
        inverter_max_kw: float | None,
        geometry: SolarGeometryService,
    ) -> None:
        self._arrays = arrays
        self._loss = max(0.0, min(50.0, system_loss_percent)) / 100.0
        self._inverter_max_kw = inverter_max_kw
        self._geometry = geometry
        self._poa = PoaTranspositionService(geometry)

    def expected_power_w(
        self,
        ts: datetime,
        *,
        ghi_wm2: float,
        dni_wm2: float | None = None,
        dhi_wm2: float | None = None,
        temperature_c: float | None = None,
    ) -> tuple[float, float]:
        """Return (total_power_w, poa_wm2)."""
        if not self._arrays or ghi_wm2 <= 0:
            return 0.0, 0.0

        elev, _ = self._geometry.elevation_azimuth(ts)
        if elev <= 0:
            return 0.0, 0.0

        total_kw = 0.0
        poa_sum = 0.0
        for arr in self._arrays:
            poa = self._poa.poa_irradiance(
                ts=ts,
                ghi_wm2=ghi_wm2,
                dni_wm2=dni_wm2,
                dhi_wm2=dhi_wm2,
                tilt_deg=arr.tilt_deg,
                azimuth_deg=arr.azimuth_deg,
            )
            poa_sum += poa
            temp_f = _temperature_factor(temperature_c)
            kw = arr.capacity_kwp * (poa / 1000.0) * temp_f * (1.0 - self._loss)
            total_kw += max(0.0, kw)

        avg_poa = poa_sum / len(self._arrays)
        power_w = total_kw * 1000.0
        if self._inverter_max_kw is not None and self._inverter_max_kw > 0:
            power_w = min(power_w, self._inverter_max_kw * 1000.0)
        return power_w, avg_poa

    def energy_kwh(self, power_w: float) -> float:
        return (power_w / 1000.0) * INTERVAL_HOURS

    def from_weather_snapshot(self, snap: WeatherSnapshot, *, ghi: float) -> tuple[float, float]:
        return self.expected_power_w(
            snap.ts_utc,
            ghi_wm2=ghi,
            temperature_c=snap.temperature_c,
        )


def _temperature_factor(temp_c: float | None) -> float:
    if temp_c is None:
        return 1.0
    delta = temp_c - REFERENCE_TEMP_C
    return max(0.5, 1.0 + TEMP_COEFFICIENT_PER_C * delta)
