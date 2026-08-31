"""Tests for solar training sample upsert."""

from __future__ import annotations

from datetime import date

import pytest

from energy_core.config import Settings
from energy_core.db.models import Base, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.solar_intelligence_repo import SolarTrainingSampleRepository
from energy_core.solar_intelligence.types import SampleQuality, TrainingSample


@pytest.fixture
async def solar_session(tmp_path):
    db_file = tmp_path / "solar.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.commit()
        yield session_factory, site.id
    await engine.dispose()


def _sample(site_id: int, *, actual_kwh: float = 1.0, quality: SampleQuality = SampleQuality.GOOD) -> TrainingSample:
    return TrainingSample(
        site_id=site_id,
        sample_date=date(2026, 1, 15),
        hour_utc=10,
        actual_kwh=actual_kwh,
        physical_kwh=1.1,
        ghi_wm2=100.0,
        dni_wm2=80.0,
        dhi_wm2=20.0,
        poa_wm2=95.0,
        solar_elevation_deg=25.0,
        cloud_cover_pct=10.0,
        temperature_c=5.0,
        quality=quality,
        provenance="test",
    )


@pytest.mark.asyncio
async def test_upsert_samples_is_idempotent(solar_session):
    session_factory, site_id = solar_session
    async with session_factory() as session:
        repo = SolarTrainingSampleRepository(session)
        first = _sample(site_id, actual_kwh=1.0)
        updated = _sample(site_id, actual_kwh=2.5, quality=SampleQuality.ESTIMATED)
        assert await repo.upsert_samples([first]) == 1
        assert await repo.upsert_samples([updated]) == 1
        await session.commit()

    async with session_factory() as session:
        repo = SolarTrainingSampleRepository(session)
        rows = await repo.list_for_site(site_id, days=365, reference_date=date(2026, 1, 20))
        assert len(rows) == 1
        assert rows[0].actual_kwh == 2.5
        assert rows[0].quality == SampleQuality.ESTIMATED


@pytest.mark.asyncio
async def test_upsert_samples_empty_returns_zero(solar_session):
    session_factory, _site_id = solar_session
    async with session_factory() as session:
        repo = SolarTrainingSampleRepository(session)
        assert await repo.upsert_samples([]) == 0
