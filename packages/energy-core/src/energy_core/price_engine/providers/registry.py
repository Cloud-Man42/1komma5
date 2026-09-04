"""Compose price providers for a site."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.heartbeat_client import HeartbeatClient
from energy_core.price_engine.providers.heartbeat_export import HeartbeatExportPriceProvider
from energy_core.price_engine.providers.heartbeat_market import (
    HeartbeatImportPriceProvider,
    HeartbeatMarketPriceProvider,
)


@dataclass(frozen=True, slots=True)
class SitePriceProviders:
    market: HeartbeatMarketPriceProvider
    import_prices: HeartbeatImportPriceProvider
    export: HeartbeatExportPriceProvider
    sell_config: object


def build_heartbeat_providers(client: HeartbeatClient, site) -> SitePriceProviders:
    return SitePriceProviders(
        market=HeartbeatMarketPriceProvider(client),
        import_prices=HeartbeatImportPriceProvider(client),
        export=HeartbeatExportPriceProvider(client),
        sell_config=sell_price_config_from_site(site),
    )
