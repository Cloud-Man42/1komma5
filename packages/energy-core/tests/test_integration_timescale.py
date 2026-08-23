import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_timescaledb_hypertable_exists():
    """Requires DATABASE_URL pointing to PostgreSQL/TimescaleDB with ENABLE_TIMESCALEDB=true."""
    import os

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url.startswith("postgresql"):
        pytest.skip("Integration test requires PostgreSQL DATABASE_URL")

    from energy_core.config import Settings
    from energy_core.db.session import create_engine
    from sqlalchemy import text

    settings = Settings(_env_file=None, DATABASE_URL=db_url, ENABLE_TIMESCALEDB=True)
    engine = create_engine(settings)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name = 'energy_readings'"
            )
        )
        row = result.first()
        if row is None:
            pytest.skip(
                "TimescaleDB hypertable not created — run migrations with ENABLE_TIMESCALEDB=true"
            )
        assert row[0] == "energy_readings"
    await engine.dispose()
