"""Shared backend API test helpers (non-fixture)."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.domain import NormalizedEnergyReading
from httpx import AsyncClient


async def seed_readings(
    session_factory,
    settings,
    slug: str,
    readings: list[tuple[int, int, float, float, float, float, float]],
    *,
    day: int = 18,
    month: int = 8,
    year: int = 2026,
) -> None:
    """Seed readings as (hour, minute, solar_w, consumption_w, import_w, export_w, battery_soc)."""
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug(slug)
        assert site is not None
        repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for hour, minute, solar, consumption, imp, exp, soc in readings:
            await repo.upsert_reading(
                site.id,
                NormalizedEnergyReading(
                    site_slug=slug,
                    recorded_at=datetime(year, month, day, hour, minute, tzinfo=UTC),
                    solar_production_w=solar,
                    consumption_w=consumption,
                    grid_import_w=imp,
                    grid_export_w=exp,
                    battery_soc_pct=soc,
                    battery_power_w=0,
                ),
            )
        await session.commit()


async def enable_solar_config(
    ac: AsyncClient,
    slug: str,
    *,
    latitude: float = 55.605,
    longitude: float = 13.0038,
    kwp: float = 8.0,
    enabled: bool = True,
) -> dict:
    res = await ac.put(
        f"/api/sites/{slug}/solar/config",
        json={
            "latitude": latitude,
            "longitude": longitude,
            "installed_peak_power_kw": kwp,
            "azimuth_deg": 180,
            "tilt_deg": 30,
            "enabled": enabled,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


async def create_charger(
    ac: AsyncClient,
    slug: str,
    *,
    name: str = "Test Halo",
    bridge_enabled: bool = False,
    chargeamp_id: str = "mock-halo",
) -> dict:
    res = await ac.post(
        f"/api/sites/{slug}/ev-chargers",
        json={
            "name": name,
            "control_source": "chargeamp",
            "bridge_enabled": bridge_enabled,
            "chargeamp_charger_id": chargeamp_id,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()
