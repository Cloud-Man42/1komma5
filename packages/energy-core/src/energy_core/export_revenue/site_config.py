"""Build SellPriceConfig from site model fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

from energy_core.export_revenue.calculator import SellPriceConfig, PricingMode

if TYPE_CHECKING:
    from energy_core.db.models import SiteModel


def sell_price_config_from_site(site: "SiteModel") -> SellPriceConfig:
    raw_mode = getattr(site, "sell_pricing_mode", "feed_in") or "feed_in"
    mode: PricingMode = (
        "feed_in" if raw_mode == "feed_in" else "flat" if raw_mode == "flat" else "spot"
    )
    return SellPriceConfig(
        pricing_mode=mode,
        provider=getattr(site, "sell_provider", "") or "",
        spot_price_adjustment_ore_per_kwh=float(getattr(site, "sell_adjustment_ore_per_kwh", 0.0) or 0.0),
        supplier_deduction_ore_per_kwh=float(getattr(site, "sell_deduction_ore_per_kwh", 0.0) or 0.0),
        grid_benefit_ore_per_kwh=float(getattr(site, "grid_benefit_ore_per_kwh", 0.0) or 0.0),
        country=getattr(site, "energy_economics_country", "SE") or "SE",
        historical_tax_credit_enabled=bool(getattr(site, "historical_tax_credit_enabled", True)),
        fallback_flat_price_sek_kwh=float(site.export_compensation_sek_kwh),
        sell_contract_start_date=getattr(site, "sell_contract_start_date", None),
    )
