"""Diagnose why the display weather section is unavailable.

Run inside the EMIC backend container:
    docker compose exec -T backend python /probe-weather.py
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime


async def main() -> None:
    from energy_core.config import Settings
    from energy_core.db.session import create_engine, create_session_factory
    from energy_core.db.repositories import SiteRepository
    from energy_core.db.solar_forecast_repo import SolarSiteConfigRepository

    settings = Settings()
    factory = create_session_factory(create_engine(settings))

    async with factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        print(f"site: {site.slug if site else None}, tz={getattr(site, 'timezone', None)}")
        if site is None:
            return

        config = await SolarSiteConfigRepository(session).get(site.id, timezone=site.timezone)
        if config is None:
            print("solar site config: MISSING")
            return
        print(
            f"solar config: enabled={config.enabled} lat={config.latitude} "
            f"lon={config.longitude} peak_kw={getattr(config, 'installed_peak_power_kw', None)}"
        )
        if not config.enabled or config.latitude is None or config.longitude is None:
            print("-> weather unavailable because config is disabled or has no coordinates")
            return

        from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
        from energy_core.solar_forecast.weather_conditions import build_current_weather

        coordinator = SolarForecastCoordinator(settings)
        try:
            resolved = await coordinator.resolve_weather(session, site, now=datetime.now(UTC))
        except Exception as exc:  # noqa: BLE001 - diagnostic script
            print(f"resolve_weather raised: {type(exc).__name__}: {exc}")
            return

        if resolved is None:
            print("-> resolve_weather returned None (no cached weather, fetch failed)")
            return

        weather, source, age = resolved
        print(f"weather resolved: source={source} age={age}")
        print(f"hours: {len(getattr(weather, 'hours', []) or [])}")
        current = build_current_weather(weather, now=datetime.now(UTC))
        print(f"build_current_weather -> {current}")


asyncio.run(main())
