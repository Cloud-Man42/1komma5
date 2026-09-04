"""Shared financial stats integration logic."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any, Literal
from zoneinfo import ZoneInfo

from energy_core.export_revenue.calculator import (
    ExportRevenueAccumulator,
    SellPriceConfig,
    accumulate_export_interval,
    finalize_export_totals,
)
from energy_core.export_revenue.tax_credit import allocate_yearly_tax_credit, compute_yearly_tax_credit_sek
from energy_core.market_prices.currency import (
    all_in_price_eur,
    feed_in_price_sek_kwh,
    spot_price_eur,
    stored_eur_to_sek_kwh,
)

PeakPeriod = Literal["day", "month", "year"]
MAX_INTERVAL_SECONDS = 300.0


@dataclass(frozen=True, slots=True)
class FinancialStatResult:
    period_start: str
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    exported_kwh: float
    imported_kwh: float
    solar_savings_sek: float
    battery_savings_sek: float
    export_revenue_sek: float
    grid_import_cost_sek: float
    market_priced_fraction: float
    energy_sale_revenue_sek: float
    grid_benefit_revenue_sek: float
    tax_credit_sek: float
    effective_sell_price_sek_kwh: float | None
    export_spot_priced_fraction: float
    uncontracted_exported_kwh: float


@dataclass(frozen=True, slots=True)
class FinancialDailyAccumulator:
    day: str
    solar_self_kwh: float = 0.0
    battery_self_kwh: float = 0.0
    export_kwh: float = 0.0
    import_kwh: float = 0.0
    solar_savings_sek: float = 0.0
    battery_savings_sek: float = 0.0
    grid_import_cost_sek: float = 0.0
    market_priced_kwh: float = 0.0
    priced_denominator_kwh: float = 0.0
    energy_sale_sek: float = 0.0
    grid_benefit_sek: float = 0.0
    spot_priced_kwh: float = 0.0
    fallback_priced_kwh: float = 0.0
    negative_price_kwh: float = 0.0
    contracted_export_kwh: float = 0.0
    uncontracted_export_kwh: float = 0.0


def build_price_maps(price_rows: list[Any]) -> tuple[dict[datetime, float], dict[datetime, float], dict[datetime, float]]:
    purchase_prices: dict[datetime, float] = {}
    spot_prices: dict[datetime, float] = {}
    feed_in_prices: dict[datetime, float] = {}
    for row in price_rows:
        timestamp = row.recorded_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        hour_key = timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        all_in_eur = all_in_price_eur(row)
        if all_in_eur is not None:
            purchase_prices[hour_key] = float(stored_eur_to_sek_kwh(float(all_in_eur)) or 0.0)
        spot_eur = spot_price_eur(row)
        if spot_eur is not None:
            spot_prices[hour_key] = float(stored_eur_to_sek_kwh(float(spot_eur)) or 0.0)
        feed_in_sek = feed_in_price_sek_kwh(row)
        if feed_in_sek is not None:
            feed_in_prices[hour_key] = feed_in_sek
    return purchase_prices, spot_prices, feed_in_prices


def integrate_financial_stats(
    readings: list[Any],
    *,
    period: PeakPeriod,
    timezone: str,
    purchase_prices: dict[datetime, float],
    spot_prices: dict[datetime, float],
    feed_in_prices: dict[datetime, float],
    fallback_purchase_price_sek_kwh: float,
    config: SellPriceConfig,
) -> list[FinancialStatResult]:
    if len(readings) < 2:
        return []

    zone = ZoneInfo(timezone)
    totals: dict[str, list[float]] = {}
    export_acc: dict[str, ExportRevenueAccumulator] = {}
    pre_contract_export: dict[str, float] = defaultdict(float)
    yearly_export: dict[int, float] = defaultdict(float)
    yearly_import: dict[int, float] = defaultdict(float)
    contract_start = config.sell_contract_start_date

    for previous, current in pairwise(readings):
        started_at = previous.recorded_at
        ended_at = current.recorded_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if ended_at.tzinfo is None:
            ended_at = ended_at.replace(tzinfo=UTC)
        seconds = (ended_at - started_at).total_seconds()
        if seconds <= 0 or seconds > MAX_INTERVAL_SECONDS:
            continue
        hours = seconds / 3600.0
        local_time = started_at.astimezone(zone)
        if period == "day":
            key = local_time.strftime("%Y-%m-%d")
        elif period == "month":
            key = local_time.strftime("%Y-%m")
        else:
            key = local_time.strftime("%Y")

        solar_w = max(0.0, float(previous.solar_production_w or 0.0))
        consumption_w = max(0.0, float(previous.consumption_w or 0.0))
        discharge_w = max(0.0, -float(previous.battery_power_w or 0.0))
        imported_w = max(0.0, float(previous.grid_import_w or 0.0))
        exported_w = max(0.0, float(previous.grid_export_w or 0.0))
        solar_self_w = min(solar_w, max(0.0, consumption_w - discharge_w - imported_w))
        battery_self_w = min(discharge_w, max(0.0, consumption_w - solar_self_w))
        solar_kwh = solar_self_w * hours / 1000.0
        battery_kwh = battery_self_w * hours / 1000.0
        export_kwh = exported_w * hours / 1000.0
        import_kwh = imported_w * hours / 1000.0

        price_key = started_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        market_price = purchase_prices.get(price_key)
        if config.pricing_mode == "feed_in":
            export_price = feed_in_prices.get(price_key)
        elif config.pricing_mode == "spot":
            export_price = spot_prices.get(price_key)
        else:
            export_price = None
        purchase_price = market_price if market_price is not None else fallback_purchase_price_sek_kwh

        values = totals.setdefault(key, [0.0] * 10)
        values[0] += solar_kwh
        values[1] += battery_kwh
        values[2] += export_kwh
        values[3] += import_kwh
        values[4] += solar_kwh * purchase_price
        values[5] += battery_kwh * purchase_price
        values[7] += import_kwh * purchase_price
        values[8] += solar_kwh + battery_kwh + import_kwh
        if market_price is not None:
            values[9] += solar_kwh + battery_kwh + import_kwh

        year_key = local_time.year
        yearly_import[year_key] += import_kwh
        export_under_contract = contract_start is None or local_time.date() >= contract_start
        if export_under_contract:
            yearly_export[year_key] += export_kwh
            acc = export_acc.setdefault(key, ExportRevenueAccumulator())
            _, acc = accumulate_export_interval(export_kwh, export_price, config, acc)
            export_acc[key] = acc
        elif export_kwh > 0:
            pre_contract_export[key] += export_kwh

    yearly_tax_credit: dict[int, float] = {}
    for year, export_kwh in yearly_export.items():
        yearly_tax_credit[year] = compute_yearly_tax_credit_sek(
            year,
            export_kwh,
            yearly_import.get(year, 0.0),
            country=config.country,
            enabled=config.historical_tax_credit_enabled,
        )

    result: list[FinancialStatResult] = []
    for key, values in sorted(totals.items()):
        export_totals = finalize_export_totals(export_acc.get(key, ExportRevenueAccumulator()))
        year = int(key[:4])
        period_tax = allocate_yearly_tax_credit(
            values[2],
            yearly_export.get(year, 0.0),
            yearly_tax_credit.get(year, 0.0),
        )
        result.append(
            FinancialStatResult(
                period_start=key,
                solar_self_consumed_kwh=round(values[0], 3),
                battery_self_consumed_kwh=round(values[1], 3),
                exported_kwh=round(values[2], 3),
                imported_kwh=round(values[3], 3),
                solar_savings_sek=round(values[4], 2),
                battery_savings_sek=round(values[5], 2),
                export_revenue_sek=round(export_totals.export_revenue_sek, 2),
                grid_import_cost_sek=round(values[7], 2),
                market_priced_fraction=round(values[9] / values[8], 3) if values[8] > 0 else 0.0,
                energy_sale_revenue_sek=round(export_totals.energy_sale_revenue_sek, 2),
                grid_benefit_revenue_sek=round(export_totals.grid_benefit_revenue_sek, 2),
                tax_credit_sek=period_tax,
                effective_sell_price_sek_kwh=export_totals.effective_sell_price_sek_kwh,
                export_spot_priced_fraction=export_totals.spot_priced_fraction,
                uncontracted_exported_kwh=round(pre_contract_export.get(key, 0.0), 3),
            )
        )
    return result


def integrate_financial_daily_accumulators(
    readings: list[Any],
    *,
    timezone: str,
    purchase_prices: dict[datetime, float],
    spot_prices: dict[datetime, float],
    feed_in_prices: dict[datetime, float],
    fallback_purchase_price_sek_kwh: float,
    config: SellPriceConfig,
) -> dict[str, FinancialDailyAccumulator]:
    if len(readings) < 2:
        return {}

    zone = ZoneInfo(timezone)
    daily: dict[str, FinancialDailyAccumulator] = {}
    contract_start = config.sell_contract_start_date

    for previous, current in pairwise(readings):
        started_at = previous.recorded_at
        ended_at = current.recorded_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if ended_at.tzinfo is None:
            ended_at = ended_at.replace(tzinfo=UTC)
        seconds = (ended_at - started_at).total_seconds()
        if seconds <= 0 or seconds > MAX_INTERVAL_SECONDS:
            continue
        hours = seconds / 3600.0
        day_key = started_at.astimezone(zone).strftime("%Y-%m-%d")

        solar_w = max(0.0, float(previous.solar_production_w or 0.0))
        consumption_w = max(0.0, float(previous.consumption_w or 0.0))
        discharge_w = max(0.0, -float(previous.battery_power_w or 0.0))
        imported_w = max(0.0, float(previous.grid_import_w or 0.0))
        exported_w = max(0.0, float(previous.grid_export_w or 0.0))
        solar_self_w = min(solar_w, max(0.0, consumption_w - discharge_w - imported_w))
        battery_self_w = min(discharge_w, max(0.0, consumption_w - solar_self_w))
        solar_kwh = solar_self_w * hours / 1000.0
        battery_kwh = battery_self_w * hours / 1000.0
        export_kwh = exported_w * hours / 1000.0
        import_kwh = imported_w * hours / 1000.0

        price_key = started_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        market_price = purchase_prices.get(price_key)
        if config.pricing_mode == "feed_in":
            export_price = feed_in_prices.get(price_key)
        elif config.pricing_mode == "spot":
            export_price = spot_prices.get(price_key)
        else:
            export_price = None
        purchase_price = market_price if market_price is not None else fallback_purchase_price_sek_kwh

        acc = daily.setdefault(day_key, FinancialDailyAccumulator(day=day_key))
        acc = FinancialDailyAccumulator(
            day=day_key,
            solar_self_kwh=acc.solar_self_kwh + solar_kwh,
            battery_self_kwh=acc.battery_self_kwh + battery_kwh,
            export_kwh=acc.export_kwh + export_kwh,
            import_kwh=acc.import_kwh + import_kwh,
            solar_savings_sek=acc.solar_savings_sek + solar_kwh * purchase_price,
            battery_savings_sek=acc.battery_savings_sek + battery_kwh * purchase_price,
            grid_import_cost_sek=acc.grid_import_cost_sek + import_kwh * purchase_price,
            market_priced_kwh=acc.market_priced_kwh + (solar_kwh + battery_kwh + import_kwh if market_price is not None else 0.0),
            priced_denominator_kwh=acc.priced_denominator_kwh + solar_kwh + battery_kwh + import_kwh,
            energy_sale_sek=acc.energy_sale_sek,
            grid_benefit_sek=acc.grid_benefit_sek,
            spot_priced_kwh=acc.spot_priced_kwh,
            fallback_priced_kwh=acc.fallback_priced_kwh,
            negative_price_kwh=acc.negative_price_kwh,
            contracted_export_kwh=acc.contracted_export_kwh,
            uncontracted_export_kwh=acc.uncontracted_export_kwh,
        )

        local_time = started_at.astimezone(zone)
        export_under_contract = contract_start is None or local_time.date() >= contract_start
        if export_under_contract and export_kwh > 0:
            export_acc = ExportRevenueAccumulator(
                exported_kwh=acc.contracted_export_kwh,
                energy_sale_revenue_sek=acc.energy_sale_sek,
                grid_benefit_revenue_sek=acc.grid_benefit_sek,
                spot_priced_kwh=acc.spot_priced_kwh,
                fallback_priced_kwh=acc.fallback_priced_kwh,
                negative_price_kwh=acc.negative_price_kwh,
            )
            interval_result, export_acc = accumulate_export_interval(export_kwh, export_price, config, export_acc)
            _ = interval_result
            acc = FinancialDailyAccumulator(
                day=day_key,
                solar_self_kwh=acc.solar_self_kwh,
                battery_self_kwh=acc.battery_self_kwh,
                export_kwh=acc.export_kwh,
                import_kwh=acc.import_kwh,
                solar_savings_sek=acc.solar_savings_sek,
                battery_savings_sek=acc.battery_savings_sek,
                grid_import_cost_sek=acc.grid_import_cost_sek,
                market_priced_kwh=acc.market_priced_kwh,
                priced_denominator_kwh=acc.priced_denominator_kwh,
                energy_sale_sek=export_acc.energy_sale_revenue_sek,
                grid_benefit_sek=export_acc.grid_benefit_revenue_sek,
                spot_priced_kwh=export_acc.spot_priced_kwh,
                fallback_priced_kwh=export_acc.fallback_priced_kwh,
                negative_price_kwh=export_acc.negative_price_kwh,
                contracted_export_kwh=export_acc.exported_kwh,
                uncontracted_export_kwh=acc.uncontracted_export_kwh,
            )
        elif export_kwh > 0:
            acc = FinancialDailyAccumulator(
                day=day_key,
                solar_self_kwh=acc.solar_self_kwh,
                battery_self_kwh=acc.battery_self_kwh,
                export_kwh=acc.export_kwh,
                import_kwh=acc.import_kwh,
                solar_savings_sek=acc.solar_savings_sek,
                battery_savings_sek=acc.battery_savings_sek,
                grid_import_cost_sek=acc.grid_import_cost_sek,
                market_priced_kwh=acc.market_priced_kwh,
                priced_denominator_kwh=acc.priced_denominator_kwh,
                energy_sale_sek=acc.energy_sale_sek,
                grid_benefit_sek=acc.grid_benefit_sek,
                spot_priced_kwh=acc.spot_priced_kwh,
                fallback_priced_kwh=acc.fallback_priced_kwh,
                negative_price_kwh=acc.negative_price_kwh,
                contracted_export_kwh=acc.contracted_export_kwh,
                uncontracted_export_kwh=acc.uncontracted_export_kwh + export_kwh,
            )
        daily[day_key] = acc
    return daily


def aggregate_daily_to_period_stats(
    daily_rows: list[FinancialDailyAccumulator],
    *,
    period: PeakPeriod,
    config: SellPriceConfig,
) -> list[FinancialStatResult]:
    grouped: dict[str, list[FinancialDailyAccumulator]] = defaultdict(list)
    for row in daily_rows:
        if period == "day":
            key = row.day
        elif period == "month":
            key = row.day[:7]
        else:
            key = row.day[:4]
        grouped[key].append(row)

    yearly_export: dict[int, float] = defaultdict(float)
    yearly_import: dict[int, float] = defaultdict(float)
    for row in daily_rows:
        year = int(row.day[:4])
        yearly_import[year] += row.import_kwh
        yearly_export[year] += row.contracted_export_kwh

    yearly_tax_credit: dict[int, float] = {}
    for year, export_kwh in yearly_export.items():
        yearly_tax_credit[year] = compute_yearly_tax_credit_sek(
            year,
            export_kwh,
            yearly_import.get(year, 0.0),
            country=config.country,
            enabled=config.historical_tax_credit_enabled,
        )

    results: list[FinancialStatResult] = []
    for key in sorted(grouped):
        rows = grouped[key]
        solar_self = sum(r.solar_self_kwh for r in rows)
        battery_self = sum(r.battery_self_kwh for r in rows)
        export_kwh = sum(r.export_kwh for r in rows)
        import_kwh = sum(r.import_kwh for r in rows)
        energy_sale = sum(r.energy_sale_sek for r in rows)
        grid_benefit = sum(r.grid_benefit_sek for r in rows)
        contracted_export = sum(r.contracted_export_kwh for r in rows)
        spot_priced = sum(r.spot_priced_kwh for r in rows)
        market_priced = sum(r.market_priced_kwh for r in rows)
        priced_denominator = sum(r.priced_denominator_kwh for r in rows)
        uncontracted = sum(r.uncontracted_export_kwh for r in rows)
        export_revenue = energy_sale + grid_benefit
        effective_price = energy_sale / contracted_export if contracted_export > 0 else None
        spot_fraction = spot_priced / contracted_export if contracted_export > 0 else 0.0
        year = int(key[:4])
        period_tax = allocate_yearly_tax_credit(
            export_kwh,
            yearly_export.get(year, 0.0),
            yearly_tax_credit.get(year, 0.0),
        )
        results.append(
            FinancialStatResult(
                period_start=key,
                solar_self_consumed_kwh=round(solar_self, 3),
                battery_self_consumed_kwh=round(battery_self, 3),
                exported_kwh=round(export_kwh, 3),
                imported_kwh=round(import_kwh, 3),
                solar_savings_sek=round(sum(r.solar_savings_sek for r in rows), 2),
                battery_savings_sek=round(sum(r.battery_savings_sek for r in rows), 2),
                export_revenue_sek=round(export_revenue, 2),
                grid_import_cost_sek=round(sum(r.grid_import_cost_sek for r in rows), 2),
                market_priced_fraction=round(market_priced / priced_denominator, 3) if priced_denominator > 0 else 0.0,
                energy_sale_revenue_sek=round(energy_sale, 2),
                grid_benefit_revenue_sek=round(grid_benefit, 2),
                tax_credit_sek=period_tax,
                effective_sell_price_sek_kwh=round(effective_price, 6) if effective_price is not None else None,
                export_spot_priced_fraction=round(spot_fraction, 4),
                uncontracted_exported_kwh=round(uncontracted, 3),
            )
        )
    return results
