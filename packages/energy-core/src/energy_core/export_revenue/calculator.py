"""Interval-matched export revenue calculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal
DataQuality = Literal["ACTUAL", "CALCULATED", "ESTIMATED", "MISSING"]
PricingMode = Literal["spot", "flat", "feed_in"]


def ore_to_kr(ore_per_kwh: float) -> float:
    return ore_per_kwh / 100.0


@dataclass(frozen=True, slots=True)
class SellPriceConfig:
    """Per-site export pricing configuration."""

    pricing_mode: PricingMode = "spot"
    provider: str = ""
    spot_price_adjustment_ore_per_kwh: float = 0.0
    supplier_deduction_ore_per_kwh: float = 0.0
    grid_benefit_ore_per_kwh: float = 0.0
    country: str = "SE"
    historical_tax_credit_enabled: bool = True
    fallback_flat_price_sek_kwh: float = 0.8
    sell_contract_start_date: date | None = None


@dataclass(frozen=True, slots=True)
class ExportIntervalResult:
    exported_kwh: float
    spot_price_sek_kwh: float | None
    effective_sell_price_sek_kwh: float
    energy_sale_revenue_sek: float
    grid_benefit_revenue_sek: float
    spot_quality: DataQuality
    adjustment_quality: DataQuality
    grid_benefit_quality: DataQuality


@dataclass
class ExportRevenueAccumulator:
    exported_kwh: float = 0.0
    energy_sale_revenue_sek: float = 0.0
    grid_benefit_revenue_sek: float = 0.0
    spot_priced_kwh: float = 0.0
    fallback_priced_kwh: float = 0.0
    negative_price_kwh: float = 0.0


@dataclass(frozen=True, slots=True)
class ExportRevenueTotals:
    exported_kwh: float
    energy_sale_revenue_sek: float
    grid_benefit_revenue_sek: float
    export_revenue_sek: float
    effective_sell_price_sek_kwh: float | None
    spot_priced_fraction: float
    spot_quality: DataQuality
    adjustment_quality: DataQuality
    grid_benefit_quality: DataQuality


def effective_sell_price_sek_kwh(
    market_price_sek_kwh: float | None,
    config: SellPriceConfig,
) -> tuple[float, DataQuality, DataQuality]:
    """Return sell price and quality flags for feed-in/spot/adjustment."""
    adjustment_kr = ore_to_kr(config.spot_price_adjustment_ore_per_kwh)
    deduction_kr = ore_to_kr(config.supplier_deduction_ore_per_kwh)

    if config.pricing_mode == "flat" or market_price_sek_kwh is None:
        price = config.fallback_flat_price_sek_kwh + adjustment_kr - deduction_kr
        if config.pricing_mode == "flat":
            spot_quality: DataQuality = "CALCULATED"
        elif market_price_sek_kwh is None:
            spot_quality = "ESTIMATED" if config.fallback_flat_price_sek_kwh > 0 else "MISSING"
        else:
            spot_quality = "ACTUAL"
        return price, spot_quality, "CALCULATED"

    price = market_price_sek_kwh + adjustment_kr - deduction_kr
    if config.pricing_mode == "feed_in":
        spot_quality = "ACTUAL"
    else:
        spot_quality = "ACTUAL"
    if config.spot_price_adjustment_ore_per_kwh == 0 and config.supplier_deduction_ore_per_kwh == 0:
        adjustment_quality: DataQuality = "MISSING" if config.provider else "CALCULATED"
    else:
        adjustment_quality = "CALCULATED"
    return price, spot_quality, adjustment_quality


def accumulate_export_interval(
    exported_kwh: float,
    market_price_sek_kwh: float | None,
    config: SellPriceConfig,
    accumulator: ExportRevenueAccumulator | None = None,
) -> tuple[ExportIntervalResult, ExportRevenueAccumulator]:
    """Calculate revenue for one export interval and update accumulator."""
    acc = accumulator or ExportRevenueAccumulator()
    if exported_kwh <= 0:
        return ExportIntervalResult(
            exported_kwh=0.0,
            spot_price_sek_kwh=market_price_sek_kwh,
            effective_sell_price_sek_kwh=0.0,
            energy_sale_revenue_sek=0.0,
            grid_benefit_revenue_sek=0.0,
            spot_quality="MISSING",
            adjustment_quality="MISSING",
            grid_benefit_quality="MISSING",
        ), acc

    sell_price, spot_quality, adjustment_quality = effective_sell_price_sek_kwh(
        market_price_sek_kwh,
        config,
    )
    energy_sale = exported_kwh * sell_price
    grid_benefit_kr = ore_to_kr(config.grid_benefit_ore_per_kwh)
    grid_benefit = exported_kwh * grid_benefit_kr
    grid_benefit_quality: DataQuality = (
        "CALCULATED" if config.grid_benefit_ore_per_kwh > 0 else "MISSING"
    )

    acc.exported_kwh += exported_kwh
    acc.energy_sale_revenue_sek += energy_sale
    acc.grid_benefit_revenue_sek += grid_benefit
    uses_market_price = (
        market_price_sek_kwh is not None and config.pricing_mode in ("spot", "feed_in")
    )
    if uses_market_price:
        acc.spot_priced_kwh += exported_kwh
        if sell_price < 0:
            acc.negative_price_kwh += exported_kwh
    else:
        acc.fallback_priced_kwh += exported_kwh

    return ExportIntervalResult(
        exported_kwh=exported_kwh,
        spot_price_sek_kwh=market_price_sek_kwh,
        effective_sell_price_sek_kwh=sell_price,
        energy_sale_revenue_sek=energy_sale,
        grid_benefit_revenue_sek=grid_benefit,
        spot_quality=spot_quality,
        adjustment_quality=adjustment_quality,
        grid_benefit_quality=grid_benefit_quality,
    ), acc


def finalize_export_totals(
    acc: ExportRevenueAccumulator,
    *,
    spot_quality: DataQuality = "MISSING",
    adjustment_quality: DataQuality = "MISSING",
    grid_benefit_quality: DataQuality = "MISSING",
) -> ExportRevenueTotals:
    """Finalize accumulated export revenue with weighted average sell price."""
    export_revenue = acc.energy_sale_revenue_sek + acc.grid_benefit_revenue_sek
    effective_price = (
        acc.energy_sale_revenue_sek / acc.exported_kwh if acc.exported_kwh > 0 else None
    )
    spot_fraction = acc.spot_priced_kwh / acc.exported_kwh if acc.exported_kwh > 0 else 0.0
    if acc.spot_priced_kwh > 0:
        resolved_spot_quality: DataQuality = "ACTUAL"
    elif acc.fallback_priced_kwh > 0:
        resolved_spot_quality = "ESTIMATED"
    else:
        resolved_spot_quality = spot_quality

    return ExportRevenueTotals(
        exported_kwh=round(acc.exported_kwh, 6),
        energy_sale_revenue_sek=round(acc.energy_sale_revenue_sek, 4),
        grid_benefit_revenue_sek=round(acc.grid_benefit_revenue_sek, 4),
        export_revenue_sek=round(export_revenue, 4),
        effective_sell_price_sek_kwh=(
            round(effective_price, 6) if effective_price is not None else None
        ),
        spot_priced_fraction=round(spot_fraction, 4),
        spot_quality=resolved_spot_quality,
        adjustment_quality=adjustment_quality,
        grid_benefit_quality=grid_benefit_quality,
    )
