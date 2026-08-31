"""Consumer aggregate persistence tests.

The ORM model silently lacked `missing_pct` while the table, the writer and the
API all used it, so every aggregate write raised TypeError and
`consumer_aggregates` stayed empty. These tests write the full field set the
coordinator sends, so a drift like that fails here instead of in production.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from energy_core.config import Settings
from energy_core.consumer_accounting.aggregator import quality_percentages
from energy_core.db.consumer_repo import ConsumerAggregateRepository
from energy_core.db.models import Base, ConsumerAggregateModel, EnergyConsumerModel, SiteModel
from energy_core.db.session import create_engine, create_session_factory

PERIOD_START = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
PERIOD_END = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


@pytest.fixture
async def consumer_session(tmp_path):
    db_file = tmp_path / "aggregates.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.flush()
        consumer = EnergyConsumerModel(site_id=site.id, consumer_type="SPA", name="Arctic Spa")
        session.add(consumer)
        await session.commit()
        yield session_factory, consumer.id
    await engine.dispose()


def _fields(consumer_id: int, **overrides) -> dict:
    """Exactly what ConsumerEnergyCoordinator._update_aggregates writes."""
    quality = quality_percentages({"MEASURED": 3, "CALCULATED": 1})
    fields = {
        "consumer_id": consumer_id,
        "granularity": "day",
        "period_start": PERIOD_START,
        "period_end": PERIOD_END,
        "energy_kwh": 12.5,
        "solar_direct_kwh": 8.0,
        "solar_battery_kwh": 1.5,
        "grid_battery_kwh": 1.0,
        "grid_direct_kwh": 2.0,
        "unknown_kwh": 0.0,
        "actual_cost_sek": 18.75,
        "reference_cost_sek": 25.0,
        "savings_sek": 6.25,
        "max_power_w": 3000.0,
        "avg_power_w": 1200.0,
        "heater_runtime_seconds": 5400.0,
        "pump_runtime_seconds": 900.0,
        "measured_pct": quality["measured_pct"],
        "calculated_pct": quality["calculated_pct"],
        "estimated_pct": quality["estimated_pct"],
        "missing_pct": quality["missing_pct"],
    }
    fields.update(overrides)
    return fields


@pytest.mark.asyncio
async def test_an_aggregate_is_stored_with_every_field_the_coordinator_sends(consumer_session):
    session_factory, consumer_id = consumer_session
    async with session_factory() as session:
        await ConsumerAggregateRepository(session).upsert(**_fields(consumer_id))
        await session.commit()

    async with session_factory() as session:
        row = await ConsumerAggregateRepository(session).get_for_period(
            consumer_id, granularity="day", period_start=PERIOD_START
        )
        assert row is not None
        assert row.energy_kwh == 12.5
        assert row.measured_pct == 75.0
        assert row.calculated_pct == 25.0
        assert row.estimated_pct == 0.0
        assert row.missing_pct == 0.0


@pytest.mark.asyncio
async def test_the_model_maps_the_quality_columns_the_table_has(consumer_session):
    """A field present in the migration but missing here breaks every write."""
    session_factory, _consumer_id = consumer_session
    mapped = set(ConsumerAggregateModel.__table__.columns.keys())
    assert {"measured_pct", "calculated_pct", "estimated_pct", "missing_pct"} <= mapped


@pytest.mark.asyncio
async def test_a_second_write_for_the_same_period_updates_instead_of_duplicating(consumer_session):
    session_factory, consumer_id = consumer_session
    async with session_factory() as session:
        repo = ConsumerAggregateRepository(session)
        await repo.upsert(**_fields(consumer_id))
        await session.commit()

    async with session_factory() as session:
        repo = ConsumerAggregateRepository(session)
        await repo.upsert(**_fields(consumer_id, energy_kwh=19.0, missing_pct=12.5))
        await session.commit()

    async with session_factory() as session:
        total = await session.execute(select(func.count()).select_from(ConsumerAggregateModel))
        assert total.scalar_one() == 1
        row = await ConsumerAggregateRepository(session).get_for_period(
            consumer_id, granularity="day", period_start=PERIOD_START
        )
        assert row is not None
        assert row.energy_kwh == 19.0
        assert row.missing_pct == 12.5


@pytest.mark.asyncio
async def test_missing_samples_are_recorded_as_a_share_of_the_period(consumer_session):
    session_factory, consumer_id = consumer_session
    quality = quality_percentages({"MEASURED": 1, "MISSING": 3})
    async with session_factory() as session:
        await ConsumerAggregateRepository(session).upsert(
            **_fields(
                consumer_id,
                measured_pct=quality["measured_pct"],
                calculated_pct=quality["calculated_pct"],
                estimated_pct=quality["estimated_pct"],
                missing_pct=quality["missing_pct"],
            )
        )
        await session.commit()

    async with session_factory() as session:
        row = await ConsumerAggregateRepository(session).get_for_period(
            consumer_id, granularity="day", period_start=PERIOD_START
        )
        assert row is not None
        assert row.missing_pct == 75.0
        assert row.measured_pct == 25.0


@pytest.mark.asyncio
async def test_no_aggregate_is_returned_for_a_period_that_was_never_written(consumer_session):
    session_factory, consumer_id = consumer_session
    async with session_factory() as session:
        row = await ConsumerAggregateRepository(session).get_for_period(
            consumer_id, granularity="month", period_start=PERIOD_START
        )
        assert row is None
