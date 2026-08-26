"""Assemble energy horizon blocks for flexible load optimization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.battery_projection import BatteryProjectionConfig, BatterySoCProjector
from energy_core.flexible_load.house_load import HouseLoadForecastSeries
from energy_core.flexible_load.types import HorizonBlock
from energy_core.solar_forecast.types import INTERVAL_MINUTES, SolarForecast


@dataclass(frozen=True, slots=True)
class HorizonInputs:
    solar_forecast: SolarForecast | None
    house_load: HouseLoadForecastSeries
    price_by_hour: dict[datetime, tuple[float | None, float | None]]
    export_value_sek_kwh: float
    fallback_price_eur_kwh: float
    initial_battery_soc_pct: float | None
    higher_priority_loads_w: float = 0.0
    battery_capacity_kwh: float = 10.0


class EnergyHorizonBuilder:
    """Build aligned 15-min HorizonBlocks from forecast inputs."""

    def build(
        self,
        *,
        now: datetime,
        horizon_hours: int = 48,
        inputs: HorizonInputs,
    ) -> tuple[HorizonBlock, ...]:
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        end = now + timedelta(hours=horizon_hours)
        load_by_ts = {p.timestamp: p.expected_power_w for p in inputs.house_load.points}

        solar_points = inputs.solar_forecast.points if inputs.solar_forecast else ()
        if solar_points:
            timestamps = tuple(p.timestamp for p in solar_points if now <= p.timestamp < end)
        else:
            timestamps = tuple(p.timestamp for p in inputs.house_load.points if now <= p.timestamp < end)

        if not timestamps:
            return ()

        raw_surplus: dict[datetime, float] = {}
        blocks_data: list[tuple[datetime, float, float, float, float | None, float | None, bool, float]] = []

        for point in solar_points:
            if point.timestamp not in timestamps:
                continue
            solar_w = point.corrected_power_w
            house_w = load_by_ts.get(point.timestamp, 500.0)
            surplus = solar_w - house_w - inputs.higher_priority_loads_w
            raw_surplus[point.timestamp] = surplus

            hour_key = point.timestamp.replace(minute=0, second=0, microsecond=0)
            prices = inputs.price_by_hour.get(hour_key, (None, None))
            spot, all_in = prices
            price_estimated = spot is None and all_in is None
            if spot is None and all_in is None:
                spot = inputs.fallback_price_eur_kwh
                all_in = inputs.fallback_price_eur_kwh

            blocks_data.append(
                (
                    point.timestamp,
                    solar_w,
                    house_w,
                    surplus,
                    spot,
                    all_in,
                    price_estimated,
                    point.confidence,
                )
            )

        if not blocks_data and timestamps:
            for ts in timestamps:
                house_w = load_by_ts.get(ts, 500.0)
                hour_key = ts.replace(minute=0, second=0, microsecond=0)
                prices = inputs.price_by_hour.get(hour_key, (None, None))
                spot, all_in = prices
                price_estimated = spot is None and all_in is None
                if spot is None:
                    spot = inputs.fallback_price_eur_kwh
                    all_in = inputs.fallback_price_eur_kwh
                surplus = -house_w - inputs.higher_priority_loads_w
                raw_surplus[ts] = surplus
                blocks_data.append((ts, 0.0, house_w, surplus, spot, all_in, price_estimated, 0.3))

        projector = BatterySoCProjector()
        soc_by_ts = projector.project(
            timestamps,
            initial_soc_pct=inputs.initial_battery_soc_pct or 50.0,
            surplus_w_by_ts=raw_surplus,
            config=BatteryProjectionConfig(
                battery_capacity_kwh=inputs.battery_capacity_kwh,
                interval_hours=INTERVAL_MINUTES / 60.0,
            ),
        )

        blocks: list[HorizonBlock] = []
        for ts, solar_w, house_w, surplus, spot, all_in, price_estimated, confidence in blocks_data:
            available = max(0.0, surplus)
            blocks.append(
                HorizonBlock(
                    timestamp=ts,
                    solar_forecast_w=solar_w,
                    house_load_forecast_w=house_w,
                    higher_priority_loads_w=inputs.higher_priority_loads_w,
                    available_surplus_w=available,
                    battery_soc_pct=soc_by_ts.get(ts),
                    spot_price_eur_kwh=spot,
                    all_in_price_eur_kwh=all_in,
                    export_value_sek_kwh=inputs.export_value_sek_kwh,
                    price_estimated=price_estimated,
                    forecast_confidence=confidence,
                )
            )
        return tuple(blocks)
