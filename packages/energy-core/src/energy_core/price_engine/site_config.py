"""Per-site price engine configuration."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.price_engine.types import OptimizationMode, PriceArea


DEFAULT_PRICE_AREA_BY_COUNTRY = {
    "SE": PriceArea.SE4,
    "DK": PriceArea.DK2,
}


@dataclass(frozen=True, slots=True)
class SitePriceEngineConfig:
    site_id: int
    slug: str
    timezone: str
    price_area: PriceArea
    optimization_mode: OptimizationMode
    external_system_id: str | None


def price_area_for_site(site) -> PriceArea:
    explicit = getattr(site, "price_area", None)
    if explicit:
        try:
            return PriceArea(str(explicit).upper())
        except ValueError:
            pass
    country = getattr(site, "energy_economics_country", "SE") or "SE"
    return DEFAULT_PRICE_AREA_BY_COUNTRY.get(country.upper(), PriceArea.SE4)


def config_from_site(site) -> SitePriceEngineConfig:
    mode_raw = getattr(site, "optimization_mode", OptimizationMode.MONITOR_ONLY.value)
    try:
        mode = OptimizationMode(str(mode_raw).upper())
    except ValueError:
        mode = OptimizationMode.MONITOR_ONLY

    return SitePriceEngineConfig(
        site_id=site.id,
        slug=site.slug,
        timezone=site.timezone,
        price_area=price_area_for_site(site),
        optimization_mode=mode,
        external_system_id=site.external_system_id,
    )
