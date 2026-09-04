"""Price engine observability helpers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from energy_core.db.price_period_repo import PriceEngineStateRepository
from energy_core.price_engine.types import OptimizationMode, PriceEngineStatus

logger = logging.getLogger(__name__)


async def get_engine_status(repo: PriceEngineStateRepository, site_id: int) -> PriceEngineStatus:
    state = await repo.get(site_id)
    if state is not None:
        return state
    return PriceEngineStatus(
        site_id=site_id,
        last_market_refresh_at=None,
        last_import_refresh_at=None,
        last_export_refresh_at=None,
        last_error=None,
        missing_periods_count=0,
        data_age_seconds=None,
        optimization_mode=OptimizationMode.MONITOR_ONLY,
    )


def log_refresh_result(*, site_slug: str, periods_written: int, duration_ms: float, error: str | None) -> None:
    if error:
        logger.warning(
            "price_engine refresh failed site=%s periods=%s duration_ms=%.0f error=%s",
            site_slug,
            periods_written,
            duration_ms,
            error,
        )
    else:
        logger.info(
            "price_engine refresh ok site=%s periods=%s duration_ms=%.0f",
            site_slug,
            periods_written,
            duration_ms,
        )


def compute_data_age_seconds(last_refresh: datetime | None, *, now: datetime | None = None) -> int | None:
    if last_refresh is None:
        return None
    ref = now or datetime.now(UTC)
    if last_refresh.tzinfo is None:
        last_refresh = last_refresh.replace(tzinfo=UTC)
    return max(0, int((ref - last_refresh.astimezone(UTC)).total_seconds()))
