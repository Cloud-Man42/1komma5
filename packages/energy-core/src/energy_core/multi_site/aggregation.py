"""Pure aggregation functions for multi-site overview."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from energy_core.multi_site.models import (
    CurrencyAmount,
    DataQualitySummary,
    FreshnessSummary,
    MultiSiteAggregate,
    MultiSiteHealth,
    SiteOverviewEntry,
)


def _sum_optional(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums), 3)


def _round2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def aggregate_sites(sites: list[SiteOverviewEntry]) -> MultiSiteOverviewParts:
    available = [s for s in sites if s.available]
    requested = len(sites)
    available_count = len(available)

    battery_cap = _sum_optional([s.battery_capacity_kwh for s in available if s.battery_capacity_kwh is not None])
    battery_stored = _sum_optional([s.battery_stored_kwh for s in available if s.battery_stored_kwh is not None])
    combined_soc = None
    if battery_cap and battery_cap > 0 and battery_stored is not None:
        combined_soc = round(battery_stored / battery_cap * 100, 1)

    import_kw = _sum_optional([s.grid_import_power_kw for s in available])
    export_kw = _sum_optional([s.grid_export_power_kw for s in available])
    net_kw = None
    if import_kw is not None or export_kw is not None:
        net_kw = round((export_kw or 0) - (import_kw or 0), 3)

    charge_kw_vals: list[float | None] = []
    discharge_kw_vals: list[float | None] = []
    for s in available:
        if s.battery_power_kw is None:
            charge_kw_vals.append(None)
            discharge_kw_vals.append(None)
        elif s.battery_power_kw > 0:
            charge_kw_vals.append(s.battery_power_kw)
            discharge_kw_vals.append(0.0)
        elif s.battery_power_kw < 0:
            charge_kw_vals.append(0.0)
            discharge_kw_vals.append(abs(s.battery_power_kw))
        else:
            charge_kw_vals.append(0.0)
            discharge_kw_vals.append(0.0)

    solar_today = _sum_optional([s.solar_today_kwh for s in available])
    consumption_today = _sum_optional([s.consumption_today_kwh for s in available])
    import_today = _sum_optional([s.grid_import_today_kwh for s in available])
    export_today = _sum_optional([s.grid_export_today_kwh for s in available])

    self_consumption = None
    if solar_today and solar_today > 0 and consumption_today is not None and import_today is not None:
        self_consumed = max(0.0, solar_today - export_today) if export_today is not None else solar_today
        self_consumption = round(min(100.0, self_consumed / solar_today * 100), 1)

    self_sufficiency = None
    if consumption_today and consumption_today > 0 and solar_today is not None and export_today is not None:
        self_consumed_load = max(0.0, min(consumption_today, solar_today - (export_today or 0)))
        self_sufficiency = round(min(100.0, self_consumed_load / consumption_today * 100), 1)

    best_solar = max(
        ((s.slug, s.solar_today_kwh) for s in available if s.solar_today_kwh is not None),
        key=lambda x: x[1],
        default=(None, None),
    )
    highest_load = max(
        ((s.slug, s.consumption_power_kw) for s in available if s.consumption_power_kw is not None),
        key=lambda x: x[1],
        default=(None, None),
    )

    aggregate = MultiSiteAggregate(
        solar_power_kw=_sum_optional([s.solar_power_kw for s in available]),
        consumption_power_kw=_sum_optional([s.consumption_power_kw for s in available]),
        grid_import_power_kw=import_kw,
        grid_export_power_kw=export_kw,
        grid_net_power_kw=net_kw,
        battery_charge_power_kw=_sum_optional(charge_kw_vals),
        battery_discharge_power_kw=_sum_optional(discharge_kw_vals),
        battery_capacity_kwh=_round2(battery_cap),
        battery_stored_kwh=_round2(battery_stored),
        battery_soc_percent=combined_soc,
        solar_today_kwh=_round2(solar_today),
        consumption_today_kwh=_round2(consumption_today),
        grid_import_today_kwh=_round2(import_today),
        grid_export_today_kwh=_round2(export_today),
        battery_charged_today_kwh=_round2(_sum_optional([s.battery_charged_today_kwh for s in available])),
        battery_discharged_today_kwh=_round2(_sum_optional([s.battery_discharged_today_kwh for s in available])),
        ev_power_kw=_sum_optional([s.ev_power_kw for s in available]),
        self_consumption_percent=self_consumption,
        self_sufficiency_percent=self_sufficiency,
        best_solar_site_slug=best_solar[0],
        best_solar_site_kwh=_round2(best_solar[1]),
        highest_load_site_slug=highest_load[0],
        highest_load_site_kw=highest_load[1],
    )

    healthy = sum(1 for s in sites if s.health == "healthy")
    degraded = sum(1 for s in sites if s.health == "degraded")
    offline = sum(1 for s in sites if s.health == "offline")

    stale_count = sum(1 for s in available if s.is_stale)
    partial = available_count < requested or any(not s.available for s in sites)
    message = None
    if partial:
        message = f"Data tillgänglig för {available_count} av {requested} anläggningar"

    timestamps = [s.updated_at for s in available if s.updated_at is not None]
    ages = [s.data_age_seconds for s in available if s.data_age_seconds is not None]

    return MultiSiteOverviewParts(
        aggregate=aggregate,
        health=MultiSiteHealth(healthy=healthy, degraded=degraded, offline=offline),
        data_quality=DataQualitySummary(
            partial=partial,
            sites_requested=requested,
            sites_available=available_count,
            sites_stale=stale_count,
            message=message,
        ),
        freshness=FreshnessSummary(
            freshest_at=max(timestamps) if timestamps else None,
            oldest_at=min(timestamps) if timestamps else None,
            max_data_age_seconds=max(ages) if ages else None,
        ),
        currencies=_group_currencies(available),
    )


def _group_currencies(sites: list[SiteOverviewEntry]) -> tuple[CurrencyAmount, ...]:
    by_currency: dict[str, dict[str, float | None]] = defaultdict(lambda: {"cost": None, "savings": None})
    for site in sites:
        cur = site.currency
        if site.cost_today is not None:
            prev = by_currency[cur]["cost"]
            by_currency[cur]["cost"] = round((prev or 0) + site.cost_today, 2)
        if site.savings_today is not None:
            prev = by_currency[cur]["savings"]
            by_currency[cur]["savings"] = round((prev or 0) + site.savings_today, 2)
    return tuple(
        CurrencyAmount(currency=cur, cost_today=vals["cost"], savings_today=vals["savings"])
        for cur, vals in sorted(by_currency.items())
    )


class MultiSiteOverviewParts:
    __slots__ = ("aggregate", "health", "data_quality", "freshness", "currencies")

    def __init__(
        self,
        *,
        aggregate: MultiSiteAggregate,
        health: MultiSiteHealth,
        data_quality: DataQualitySummary,
        freshness: FreshnessSummary,
        currencies: tuple[CurrencyAmount, ...],
    ) -> None:
        self.aggregate = aggregate
        self.health = health
        self.data_quality = data_quality
        self.freshness = freshness
        self.currencies = currencies


def weighted_battery_soc(entries: list[tuple[float, float]]) -> float | None:
    """Compute SoC from (capacity_kwh, stored_kwh) pairs."""
    cap = sum(c for c, _ in entries)
    stored = sum(s for _, s in entries)
    if cap <= 0:
        return None
    return round(stored / cap * 100, 1)
