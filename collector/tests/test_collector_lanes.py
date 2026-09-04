"""Collector lane isolation tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from collector.app.collector import Collector


@pytest.mark.asyncio
async def test_poll_once_runs_all_lanes_sequentially():
    collector = Collector()
    collector.run_fast_lane = AsyncMock()
    collector.run_medium_lane = AsyncMock()
    collector.run_slow_lane = AsyncMock()
    await collector.poll_once()
    collector.run_fast_lane.assert_awaited_once()
    collector.run_medium_lane.assert_awaited_once()
    collector.run_slow_lane.assert_awaited_once()
