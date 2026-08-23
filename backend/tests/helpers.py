"""Shared backend API test helpers (non-fixture)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.domain import NormalizedEnergyReading
from httpx import AsyncClient

READING_SPACING = timedelta(minutes=5)


def recent_reading_timestamps(
    now: datetime,
    day_start: datetime,
    count: int,
    *,
    spacing: timedelta = READING_SPACING,
) -> list[datetime]:
    """Return `count` timestamps ending at `now`, oldest first.

    Never in the future and never before `day_start`, so daily aggregates pick them up
    whatever time of day the suite runs. The spacing shrinks when the day has only just
    started and there is not room for the full interval.
    """
    if count < 1:
        return []
    if count == 1:
        return [now]
    room = (now - day_start) / (count - 1)
    step = min(spacing, room)
    return [now - step * (count - 1 - index) for index in range(count)]


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


async def seed_recent_readings(
    session_factory,
    settings,
    slug: str,
    samples: list[tuple[float, float, float, float, float]],
    *,
    spacing: timedelta = READING_SPACING,
) -> list[datetime]:
    """Seed readings as (solar_w, consumption_w, import_w, export_w, battery_soc), oldest first.

    Timestamps come from the clock rather than fixed hours, so the readings are always in
    the past and always inside the site's current local day.
    """
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug(slug)
        assert site is not None
        now = datetime.now(UTC)
        zone = ZoneInfo(site.timezone)
        day_start = (
            now.astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        )
        timestamps = recent_reading_timestamps(now, day_start, len(samples), spacing=spacing)
        repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for recorded_at, (solar, consumption, imp, exp, soc) in zip(
            timestamps, samples, strict=True
        ):
            await repo.upsert_reading(
                site.id,
                NormalizedEnergyReading(
                    site_slug=slug,
                    recorded_at=recorded_at,
                    solar_production_w=solar,
                    consumption_w=consumption,
                    grid_import_w=imp,
                    grid_export_w=exp,
                    battery_soc_pct=soc,
                    battery_power_w=0,
                ),
            )
        await session.commit()
    return timestamps


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
