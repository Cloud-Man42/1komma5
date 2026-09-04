"""Forecast learning API routes."""

from __future__ import annotations

from app.deps import get_db_session, get_site_repository
from app.schemas import (
    ForecastLearningRecentResponse,
    ForecastLearningSummaryResponse,
    ForecastMetricSummaryResponse,
    ForecastSnapshotResponse,
)
from energy_core.db.repositories import SiteRepository
from energy_core.forecast_learning.service import ForecastLearningService
from energy_core.forecast_learning.types import ForecastKind
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["forecast-learning"])


def _metric_response(metric) -> ForecastMetricSummaryResponse:
    return ForecastMetricSummaryResponse(
        kind=metric.kind.value,
        mae=metric.mae,
        bias=metric.bias,
        sample_count=metric.sample_count,
        mape_pct=metric.mape_pct,
    )


def _snapshot_response(snapshot) -> ForecastSnapshotResponse:
    return ForecastSnapshotResponse(
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        kind=snapshot.kind.value,
        predicted_value=snapshot.predicted_value,
        actual_value=snapshot.actual_value,
        forecast_recorded_at=snapshot.forecast_recorded_at,
        actual_recorded_at=snapshot.actual_recorded_at,
        model_version=snapshot.model_version,
    )


@router.get("/sites/{slug}/forecast-learning/summary", response_model=ForecastLearningSummaryResponse)
async def get_forecast_learning_summary(
    slug: str,
    days: int = Query(default=30, ge=1, le=365),
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> ForecastLearningSummaryResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    from energy_core.config import get_settings

    settings = get_settings()
    service = ForecastLearningService(session, is_sqlite=settings.is_sqlite)
    summary = await service.summary(site.id, days=days)
    return ForecastLearningSummaryResponse(
        slug=slug,
        timezone=site.timezone,
        days=summary.days,
        metrics=[_metric_response(m) for m in summary.metrics],
        last_reconciled_at=summary.last_reconciled_at,
    )


@router.get("/sites/{slug}/forecast-learning/recent", response_model=ForecastLearningRecentResponse)
async def get_forecast_learning_recent(
    slug: str,
    kind: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=48, ge=1, le=200),
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> ForecastLearningRecentResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    forecast_kind: ForecastKind | None = None
    if kind is not None:
        try:
            forecast_kind = ForecastKind(kind)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown forecast kind '{kind}'") from exc

    from energy_core.config import get_settings

    settings = get_settings()
    service = ForecastLearningService(session, is_sqlite=settings.is_sqlite)
    snapshots = await service.recent(site.id, kind=forecast_kind, days=days, limit=limit)
    return ForecastLearningRecentResponse(
        slug=slug,
        timezone=site.timezone,
        kind=kind,
        snapshots=[_snapshot_response(s) for s in snapshots],
    )
