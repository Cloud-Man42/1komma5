"""Timescale retention policy tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.config import Settings
from energy_core.db.timescale_retention import ensure_timescale_compression, ensure_timescale_retention


@pytest.mark.asyncio
async def test_ensure_timescale_retention_disabled() -> None:
    settings = Settings(_env_file=None, TIMESCALE_RETENTION_ENABLED=False)
    result = await ensure_timescale_retention(AsyncMock(), settings)
    assert result["status"] == "disabled"


@pytest.mark.asyncio
async def test_ensure_timescale_retention_skips_sqlite() -> None:
    settings = Settings(
        _env_file=None,
        TIMESCALE_RETENTION_ENABLED=True,
        DATABASE_URL="sqlite+aiosqlite:///test.db",
    )
    result = await ensure_timescale_retention(AsyncMock(), settings)
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_ensure_timescale_retention_creates_missing_policies() -> None:
    settings = Settings(
        _env_file=None,
        TIMESCALE_RETENTION_ENABLED=True,
        ENABLE_TIMESCALEDB=True,
        DATABASE_URL="postgresql+asyncpg://energy:pass@localhost/energy",
    )
    session = AsyncMock()
    exists_none = MagicMock()
    exists_none.scalar_one_or_none.return_value = None
    exists_one = MagicMock()
    exists_one.scalar_one_or_none.return_value = 1
    session.execute = AsyncMock(
        side_effect=[
            exists_none,
            MagicMock(),
            exists_none,
            MagicMock(),
            exists_one,
        ]
    )

    result = await ensure_timescale_retention(session, settings)

    assert result["status"] == "applied"
    assert result["policies"]["energy_readings"] == "created"
    assert result["policies"]["consumer_samples"] == "created"
    assert result["policies"]["vehicle_state_history"] == "exists"
    assert session.execute.await_count == 5


def test_compression_policies_cover_all_hypertables() -> None:
    from energy_core.db.timescale_retention import COMPRESSION_POLICIES

    assert set(COMPRESSION_POLICIES) == {
        "energy_readings",
        "consumer_samples",
        "vehicle_state_history",
    }
    assert COMPRESSION_POLICIES["consumer_samples"]["segmentby"] == "consumer_id"
    assert COMPRESSION_POLICIES["vehicle_state_history"]["segmentby"] == "vehicle_id"


@pytest.mark.asyncio
async def test_ensure_timescale_compression_disabled() -> None:
    settings = Settings(_env_file=None, TIMESCALE_COMPRESSION_ENABLED=False)
    result = await ensure_timescale_compression(AsyncMock(), settings)
    assert result["status"] == "disabled"


@pytest.mark.asyncio
async def test_ensure_timescale_compression_enables_table_and_policy() -> None:
    from energy_core.db.timescale_retention import ensure_timescale_compression

    settings = Settings(
        _env_file=None,
        TIMESCALE_COMPRESSION_ENABLED=True,
        ENABLE_TIMESCALEDB=True,
        DATABASE_URL="postgresql+asyncpg://energy:pass@localhost/energy",
    )
    session = AsyncMock()
    compression_disabled = MagicMock()
    compression_disabled.scalar_one_or_none.return_value = False
    policy_missing = MagicMock()
    policy_missing.scalar_one_or_none.return_value = None
    policy_exists = MagicMock()
    policy_exists.scalar_one_or_none.return_value = 1
    session.execute = AsyncMock(
        side_effect=[
            compression_disabled,
            MagicMock(),
            policy_missing,
            MagicMock(),
        ]
        * 3
    )

    result = await ensure_timescale_compression(session, settings)

    assert result["status"] == "applied"
    assert result["policies"]["energy_readings:compression"] == "enabled"
    assert result["policies"]["energy_readings:policy"] == "created"
    assert result["policies"]["consumer_samples:compression"] == "enabled"
    assert result["policies"]["vehicle_state_history:policy"] == "created"
    assert session.execute.await_count == 12
