"""Import price tariff breakdown from price periods."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.market_prices.currency import stored_eur_to_sek_kwh
from energy_core.price_engine.types import PricePeriod


@dataclass(frozen=True, slots=True)
class TariffBreakdown:
    market_price_sek_kwh: float | None
    import_price_sek_kwh: float | None
    grid_surcharge_sek_kwh: float | None
    vat_rate: float | None
    uses_fallback_grid_costs: bool | None


def tariff_breakdown_from_period(period: PricePeriod | None) -> TariffBreakdown | None:
    if period is None:
        return None

    market = period.market_price_sek_kwh
    import_price = period.import_price_sek_kwh
    grid_surcharge = None
    if market is not None and import_price is not None:
        grid_surcharge = round(max(0.0, import_price - market), 4)

    vat_rate: float | None = None
    uses_fallback: bool | None = None
    for layer in period.components.values():
        if not isinstance(layer, dict):
            continue
        if vat_rate is None and layer.get("vat_rate") is not None:
            vat_rate = float(layer["vat_rate"])
        if uses_fallback is None and layer.get("uses_fallback_grid_costs") is not None:
            uses_fallback = bool(layer["uses_fallback_grid_costs"])
        grid_eur = layer.get("grid_costs_total_eur_kwh")
        if grid_surcharge is None and grid_eur is not None:
            grid_sek = stored_eur_to_sek_kwh(float(grid_eur))
            if grid_sek is not None:
                grid_surcharge = round(grid_sek, 4)

    return TariffBreakdown(
        market_price_sek_kwh=market,
        import_price_sek_kwh=import_price,
        grid_surcharge_sek_kwh=grid_surcharge,
        vat_rate=vat_rate,
        uses_fallback_grid_costs=uses_fallback,
    )
