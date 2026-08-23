from datetime import UTC, datetime

import pytest
from energy_core.config import HeartbeatProviderKind, Settings
from energy_core.domain import RawEnergyReading
from energy_core.normalization import normalize_reading
from energy_core.providers.mock import MockHeartbeatProvider


def test_settings_defaults():
    settings = Settings(_env_file=None)
    assert settings.app_env.value == "development"
    assert settings.is_sqlite is True
    assert settings.heartbeat_provider == HeartbeatProviderKind.MOCK


def test_settings_postgresql_detection():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
    )
    assert settings.is_postgresql is True
    assert settings.is_sqlite is False


def test_normalize_clamps_battery_soc():
    raw = RawEnergyReading(
        site_slug="akarp",
        recorded_at=datetime.now(UTC),
        solar_production_w=-100,
        consumption_w=-50,
        grid_import_w=-10,
        grid_export_w=-5,
        battery_soc_pct=150,
        battery_power_w=0,
    )
    normalized = normalize_reading(raw)
    assert normalized.solar_production_w == 0
    assert normalized.consumption_w == 0
    assert normalized.grid_import_w == 0
    assert normalized.grid_export_w == 0
    assert normalized.battery_soc_pct == 100


@pytest.mark.asyncio
async def test_mock_provider_returns_both_sites():
    provider = MockHeartbeatProvider(seed=42)
    sites = await provider.list_sites()
    slugs = {s.slug for s in sites}
    assert slugs == {"akarp", "summer-house-denmark"}


@pytest.mark.asyncio
async def test_mock_provider_generates_changing_values():
    provider = MockHeartbeatProvider(seed=1)
    r1 = await provider.fetch_readings(datetime(2026, 6, 15, 10, 0, tzinfo=UTC))
    r2 = await provider.fetch_readings(datetime(2026, 6, 15, 18, 0, tzinfo=UTC))
    assert len(r1) == 2
    akarp_day = next(r for r in r1 if r.site_slug == "akarp")
    akarp_evening = next(r for r in r2 if r.site_slug == "akarp")
    assert akarp_day.solar_production_w > akarp_evening.solar_production_w
