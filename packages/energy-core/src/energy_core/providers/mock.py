"""Mock heartbeat provider generating realistic values for development."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime

from energy_core.domain import RawEnergyReading, SiteSnapshot

MOCK_SITES: tuple[SiteSnapshot, ...] = (
    SiteSnapshot(
        slug="akarp",
        name="Demo Home",
        timezone="Europe/Stockholm",
        external_system_id=None,
    ),
    SiteSnapshot(
        slug="summer-house-denmark",
        name="Summer House Denmark",
        timezone="Europe/Copenhagen",
        external_system_id=None,
    ),
)


def _diurnal_factor(hour: float, peak_hour: float = 13.0, width: float = 5.0) -> float:
    """Smooth bell curve peaking around solar noon."""
    return math.exp(-0.5 * ((hour - peak_hour) / width) ** 2)


class MockHeartbeatProvider:
    """Generates changing realistic energy readings for both mock sites."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._phase_offset = self._rng.uniform(0, math.tau)

    async def list_sites(self) -> list[SiteSnapshot]:
        return list(MOCK_SITES)

    async def fetch_readings(self, recorded_at: datetime | None = None) -> list[RawEnergyReading]:
        now = recorded_at or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        hour = now.hour + now.minute / 60.0
        noise = lambda scale: self._rng.uniform(-scale, scale)

        akarp_solar_peak = 8500.0
        akarp_base_load = 1200.0
        akarp_solar = max(0.0, akarp_solar_peak * _diurnal_factor(hour, peak_hour=13.5) + noise(400))
        akarp_consumption = max(200.0, akarp_base_load + 600 * (1 - _diurnal_factor(hour, peak_hour=8.0, width=3.0)) + noise(150))
        akarp_net = akarp_consumption - akarp_solar
        akarp_import = max(0.0, akarp_net + noise(80)) if akarp_net > 0 else noise(40)
        akarp_export = max(0.0, -akarp_net + noise(80)) if akarp_net < 0 else noise(40)
        if akarp_import > 0 and akarp_export > 0:
            akarp_export = 0.0
        akarp_battery_soc = min(100.0, max(15.0, 55 + 35 * _diurnal_factor(hour) + noise(3)))
        akarp_battery_power = (akarp_solar - akarp_consumption) * 0.3 + noise(200)

        summer_solar_peak = 6200.0
        summer_base_load = 450.0
        summer_solar = max(0.0, summer_solar_peak * _diurnal_factor(hour, peak_hour=12.5, width=4.5) + noise(300))
        summer_consumption = max(100.0, summer_base_load + 250 * (1 - _diurnal_factor(hour, peak_hour=19.0, width=2.5)) + noise(80))
        summer_net = summer_consumption - summer_solar
        summer_import = max(0.0, summer_net + noise(60)) if summer_net > 0 else noise(30)
        summer_export = max(0.0, -summer_net + noise(60)) if summer_net < 0 else noise(30)
        if summer_import > 0 and summer_export > 0:
            summer_export = 0.0
        summer_battery_soc = min(100.0, max(10.0, 40 + 45 * _diurnal_factor(hour, peak_hour=14.0) + noise(4)))
        summer_battery_power = (summer_solar - summer_consumption) * 0.25 + noise(150)

        return [
            RawEnergyReading(
                site_slug="akarp",
                recorded_at=now,
                solar_production_w=akarp_solar,
                consumption_w=akarp_consumption,
                grid_import_w=akarp_import,
                grid_export_w=akarp_export,
                battery_soc_pct=akarp_battery_soc,
                battery_power_w=akarp_battery_power,
            ),
            RawEnergyReading(
                site_slug="summer-house-denmark",
                recorded_at=now,
                solar_production_w=summer_solar,
                consumption_w=summer_consumption,
                grid_import_w=summer_import,
                grid_export_w=summer_export,
                battery_soc_pct=summer_battery_soc,
                battery_power_w=summer_battery_power,
            ),
        ]
