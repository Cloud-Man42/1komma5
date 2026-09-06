from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from energy_core.config import Settings
from energy_core.db.models import Base, EnergyHourlyModel
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.solar_forecast.api_snapshot_builder import refresh_solar_forecast_intraday_metrics


@pytest.fixture
async def sqlite_session():
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site_repo = SiteRepository(session)
        site = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
        await session.commit()
        yield session, settings, site
    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_solar_forecast_intraday_metrics_recomputes_cached_values(sqlite_session):
    session, settings, site = sqlite_session
    now = datetime(2026, 6, 15, 10, 0, 0, tzinfo=UTC)
    past = now - timedelta(hours=2)
    future = now + timedelta(hours=2)

    session.add(
        EnergyHourlyModel(
            site_id=site.id,
            hour=past,
            solar_kwh=1.5,
            consumption_kwh=0.5,
            import_kwh=0.0,
            export_kwh=1.0,
        )
    )
    await session.commit()

    payload = {
        "site_id": site.id,
        "generated_at": (now - timedelta(hours=3)).isoformat(),
        "model_version": "solar-forecast-v2",
        "quality": "MEDIUM",
        "weather_source": "cache",
        "expected_today_kwh": 20.0,
        "remaining_today_kwh": 15.0,
        "expected_tomorrow_kwh": 18.0,
        "peak_power_w": 4000.0,
        "peak_time": None,
        "confidence": 0.7,
        "lower_today_kwh": 15.0,
        "upper_today_kwh": 25.0,
        "weather_summary": "Molnigt",
        "actual_today_kwh": 0.5,
        "forecast_so_far_kwh": 1.0,
        "remaining_vs_expected_kwh": 19.5,
        "age_seconds": 7200.0,
        "points": [
            {
                "timestamp": past.isoformat(),
                "baseline_power_w": 2000.0,
                "corrected_power_w": 2000.0,
                "expected_energy_kwh": 0.5,
                "lower_bound_power_w": 1500.0,
                "upper_bound_power_w": 2500.0,
                "confidence": 0.7,
                "correction_factor": 1.0,
            },
            {
                "timestamp": future.isoformat(),
                "baseline_power_w": 3000.0,
                "corrected_power_w": 3000.0,
                "expected_energy_kwh": 0.75,
                "lower_bound_power_w": 2000.0,
                "upper_bound_power_w": 3500.0,
                "confidence": 0.7,
                "correction_factor": 1.0,
            },
        ],
    }

    with patch("energy_core.solar_forecast.api_snapshot_builder.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        mock_datetime.UTC = UTC
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        refreshed = await refresh_solar_forecast_intraday_metrics(session, site, payload, settings)

    assert refreshed["actual_today_kwh"] == 1.5
    assert refreshed["forecast_so_far_kwh"] == 0.5
    assert refreshed["remaining_today_kwh"] == 0.75
    assert refreshed["expected_today_kwh"] == 1.25
    assert refreshed["age_seconds"] >= 0.0
