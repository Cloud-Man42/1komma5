"""Heartbeat-backed export price provider."""

from __future__ import annotations

from datetime import datetime

from energy_core.export_revenue.calculator import SellPriceConfig, effective_sell_price_sek_kwh, ore_to_kr
from energy_core.heartbeat.feed_in_prices import parse_feed_in_tariff
from energy_core.heartbeat.market_prices import parse_market_prices
from energy_core.heartbeat_client import HeartbeatClient
from energy_core.market_prices.currency import stored_eur_to_sek_kwh, sek_to_eur
from energy_core.price_engine.types import RawPricePoint


class HeartbeatExportPriceProvider:
    def __init__(self, client: HeartbeatClient) -> None:
        self._client = client

    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        sell_config: SellPriceConfig,
        resolution: str = "15m",
    ) -> tuple[RawPricePoint, ...]:
        native = 15 if resolution == "15m" else 60
        raw_market = await self._client.fetch_market_prices(
            system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution=resolution,
        )
        parsed = parse_market_prices(raw_market)

        feed_in_eur: float | None = None
        try:
            hb_raw = await self._client.fetch_heartbeat_prices(system_id)
            feed_in = parse_feed_in_tariff(hb_raw)
            feed_in_eur = feed_in.feed_in_tariff_eur_kwh
        except Exception:
            feed_in_eur = None

        points: list[RawPricePoint] = []
        for point in parsed.points:
            spot_sek = stored_eur_to_sek_kwh(point.spot_eur_kwh)
            export_sek, spot_q, adj_q = effective_sell_price_sek_kwh(spot_sek, sell_config)

            if sell_config.pricing_mode == "feed_in" and feed_in_eur is not None:
                feed_in_sek = stored_eur_to_sek_kwh(feed_in_eur)
                if feed_in_sek is not None:
                    export_sek = feed_in_sek

            components = {
                "spot_quality": spot_q,
                "adjustment_quality": adj_q,
                "pricing_mode": sell_config.pricing_mode,
                "adjustment_ore_per_kwh": sell_config.spot_price_adjustment_ore_per_kwh,
                "deduction_ore_per_kwh": sell_config.supplier_deduction_ore_per_kwh,
                "grid_benefit_ore_per_kwh": sell_config.grid_benefit_ore_per_kwh,
                "grid_benefit_sek_kwh": ore_to_kr(sell_config.grid_benefit_ore_per_kwh),
            }
            if feed_in_eur is not None:
                components["feed_in_tariff_eur_kwh"] = feed_in_eur

            export_eur = sek_to_eur(export_sek) if export_sek is not None else None
            points.append(
                RawPricePoint(
                    timestamp=point.timestamp,
                    market_price_eur_kwh=point.spot_eur_kwh,
                    export_price_eur_kwh=export_eur,
                    native_resolution_minutes=native,
                    components={"export": components},
                )
            )

        return tuple(points)


def hourly_export_from_spot(
    *,
    timestamps: tuple[datetime, ...],
    spot_sek_by_ts: dict[datetime, float | None],
    sell_config: SellPriceConfig,
    native_resolution_minutes: int = 60,
) -> tuple[RawPricePoint, ...]:
    """Build export points without live API (tests / fallback)."""
    points: list[RawPricePoint] = []
    for ts in timestamps:
        spot_sek = spot_sek_by_ts.get(ts.replace(minute=0, second=0, microsecond=0))
        export_sek, _, _ = effective_sell_price_sek_kwh(spot_sek, sell_config)
        export_eur = sek_to_eur(export_sek)
        points.append(
            RawPricePoint(
                timestamp=ts,
                export_price_eur_kwh=export_eur,
                native_resolution_minutes=native_resolution_minutes,
            )
        )
    return tuple(points)
