"""Probe Heartbeat price endpoints for export / heartbeat tariffs."""

from __future__ import annotations

import asyncio

from energy_core.config import get_settings
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.heartbeat_client_factory import create_heartbeat_client


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        if site is None:
            raise SystemExit("site akarp not found")
        client = await create_heartbeat_client(session)
        if client is None:
            raise SystemExit("heartbeat client unavailable")
        system_id = site.external_system_id
        assert system_id
        hb_prices = await client._request(  # noqa: SLF001
            "GET",
            f"/v3/heartbeat-prices?siteId={system_id}",
        )
        summary = await client._request(  # noqa: SLF001
            "GET",
            f"/v2/heartbeat-ai/summary?siteId={system_id}&resolution=1M",
        )
        from onekommafive.models.analytics import HeartbeatAiSummary, HeartbeatPrices

        hb_model = HeartbeatPrices.from_dict(hb_prices or {})
        summary_model = HeartbeatAiSummary.from_dict("1M", summary or {})
        print("=== heartbeat-prices tariffs (SEK/kWh) ===")
        for label, window in [
            ("day", hb_model.day),
            ("week", hb_model.week),
            ("month", hb_model.month),
        ]:
            print(
                label,
                "feed_in=",
                window.grid_feed_in_tariff_eur_per_kwh,
                "heartbeat=",
                window.heartbeat_price_eur_per_kwh,
            )
        print("=== heartbeat-ai summary 1M ===")
        print("feed_in_price", summary_model.feed_in_price_eur_per_kwh)
        print("heartbeat_price", summary_model.heartbeat_price_eur_per_kwh)
        print("sold_energy_kwh", summary_model.sold_energy_kwh)
        print("earned_amount", summary_model.earned_amount_eur)
        print("=== site config ===")
        print("export_compensation_sek_kwh", site.export_compensation_sek_kwh)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
