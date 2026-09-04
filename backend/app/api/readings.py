from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.deps import get_app_settings, get_db_session, get_reading_repository, get_site_repository
from app.schemas import (
    AggregatedReadingResponse,
    FinancialStatResponse,
    FinancialStatsResponse,
    ForecastValuesResponse,
    HistoryResponse,
    MonthlyForecastResponse,
    PeakReadingResponse,
    PeaksResponse,
    ReadingResponse,
    YearForecastResponse,
)
from energy_core.db.repositories import (
    EnergyReadingRepository,
    HistoricalEnergyRepository,
    SiteRepository,
)
from energy_core.cache.service import financial_stats_cache_key, get_cache_service
from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.forecasting import ForecastValues, build_year_forecast
from energy_core.performance.context import get_performance_context
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["readings"])


def _forecast_values_response(values: ForecastValues) -> ForecastValuesResponse:
    return ForecastValuesResponse(
        solar_self_consumed_kwh=values.solar_self_consumed_kwh,
        battery_self_consumed_kwh=values.battery_self_consumed_kwh,
        exported_kwh=values.exported_kwh,
        imported_kwh=values.imported_kwh,
        solar_savings_sek=values.solar_savings_sek,
        battery_savings_sek=values.battery_savings_sek,
        export_revenue_sek=values.export_revenue_sek,
        grid_import_cost_sek=values.grid_import_cost_sek,
        net_sek=values.net_sek,
    )


@router.get("/sites/{slug}/forecast", response_model=YearForecastResponse)
async def get_site_forecast(
    slug: str,
    year: int = Query(ge=2000, le=2100),
    session: AsyncSession = Depends(get_db_session),
    site_repo: SiteRepository = Depends(get_site_repository),
    reading_repo: EnergyReadingRepository = Depends(get_reading_repository),
) -> YearForecastResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")
    try:
        zone = ZoneInfo(site.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid site timezone: {site.timezone}") from exc
    history = await reading_repo.list_financial_stats(
        site_id=site.id,
        period="day",
        timezone=site.timezone,
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        sell_config=sell_price_config_from_site(site),
    )
    historical_records = await HistoricalEnergyRepository(
        session,
        is_sqlite=session.bind is not None and session.bind.dialect.name == "sqlite",
    ).list_for_site(site.id)
    records_by_year: dict[int, list] = {}
    for record in historical_records:
        records_by_year.setdefault(record.year, []).append(record)
    complete_years = [
        baseline_year
        for baseline_year, records in records_by_year.items()
        if {record.month for record in records} == set(range(1, 13))
    ]
    baseline_year = max(complete_years, default=None)
    baseline_records = records_by_year.get(baseline_year, []) if baseline_year is not None else []
    monthly_import_baseline = {record.month: record.imported_kwh for record in baseline_records}
    result = build_year_forecast(
        history,
        target_year=year,
        today=datetime.now(zone).date(),
        purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        monthly_import_baseline=monthly_import_baseline or None,
    )
    return YearForecastResponse(
        slug=slug,
        timezone=site.timezone,
        year=result.year,
        observed_days=result.observed_days,
        confidence=result.confidence,
        uncertainty_pct=result.uncertainty_pct,
        import_baseline_year=baseline_year,
        import_baseline_source=baseline_records[0].source if baseline_records else None,
        import_baseline_estimated=baseline_records[0].estimated if baseline_records else False,
        import_baseline_kwh=(
            round(sum(record.imported_kwh for record in baseline_records), 3)
            if baseline_records
            else None
        ),
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        actual=_forecast_values_response(result.actual),
        forecast=_forecast_values_response(result.forecast),
        total=_forecast_values_response(result.total),
        months=[
            MonthlyForecastResponse(
                month=month.month,
                actual=_forecast_values_response(month.actual),
                forecast=_forecast_values_response(month.forecast),
                total=_forecast_values_response(month.total),
            )
            for month in result.months
        ],
    )


@router.get("/sites/{slug}/financial-stats", response_model=FinancialStatsResponse)
async def get_site_financial_stats(
    slug: str,
    period: Literal["day", "month", "year"] = Query(default="day"),
    year: int | None = Query(default=None, ge=2000, le=2100),
    site_repo: SiteRepository = Depends(get_site_repository),
    reading_repo: EnergyReadingRepository = Depends(get_reading_repository),
    settings=Depends(get_app_settings),
) -> FinancialStatsResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")
    try:
        zone = ZoneInfo(site.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid site timezone: {site.timezone}") from exc
    from_time = datetime(year, 1, 1, tzinfo=zone).astimezone(UTC) if year is not None else None
    to_time = datetime(year + 1, 1, 1, tzinfo=zone).astimezone(UTC) if year is not None else None

    cache = get_cache_service(settings)
    cache_key = financial_stats_cache_key(site.id, period, year)
    ttl_seconds = settings.financial_redis_cache_ttl_seconds

    async def factory() -> dict:
        stats = await reading_repo.list_financial_stats(
            site_id=site.id,
            period=period,
            timezone=site.timezone,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
            from_time=from_time,
            to_time=to_time,
            sell_config=sell_price_config_from_site(site),
            use_aggregates=settings.financial_aggregates_enabled,
        )
        return FinancialStatsResponse(
            slug=slug,
            timezone=site.timezone,
            period=period,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
            sell_pricing_mode=getattr(site, "sell_pricing_mode", "spot") or "spot",
            sell_contract_start_date=getattr(site, "sell_contract_start_date", None),
            stats=[
                FinancialStatResponse(
                    period_start=stat.period_start,
                    solar_self_consumed_kwh=stat.solar_self_consumed_kwh,
                    battery_self_consumed_kwh=stat.battery_self_consumed_kwh,
                    exported_kwh=stat.exported_kwh,
                    imported_kwh=stat.imported_kwh,
                    solar_savings_sek=stat.solar_savings_sek,
                    battery_savings_sek=stat.battery_savings_sek,
                    export_revenue_sek=stat.export_revenue_sek,
                    grid_import_cost_sek=stat.grid_import_cost_sek,
                    market_priced_fraction=stat.market_priced_fraction,
                    energy_sale_revenue_sek=stat.energy_sale_revenue_sek,
                    grid_benefit_revenue_sek=stat.grid_benefit_revenue_sek,
                    tax_credit_sek=stat.tax_credit_sek,
                    effective_sell_price_sek_kwh=stat.effective_sell_price_sek_kwh,
                    export_spot_priced_fraction=stat.export_spot_priced_fraction,
                    uncontracted_exported_kwh=stat.uncontracted_exported_kwh,
                )
                for stat in stats
            ],
        ).model_dump(mode="json")

    ctx = get_performance_context()
    cached = await cache.get(cache_key)
    if cached is not None:
        if ctx is not None:
            ctx.cache_hit = True
        return FinancialStatsResponse.model_validate(cached)

    payload = await cache.get_or_set(cache_key, factory, ttl_seconds=ttl_seconds)
    return FinancialStatsResponse.model_validate(payload)


@router.get("/sites/{slug}/peaks", response_model=PeaksResponse)
async def get_site_peaks(
    slug: str,
    period: Literal["day", "month", "year"] = Query(default="day"),
    year: int | None = Query(default=None, ge=2000, le=2100),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    site_repo: SiteRepository = Depends(get_site_repository),
    reading_repo: EnergyReadingRepository = Depends(get_reading_repository),
) -> PeaksResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")
    if from_time is not None and to_time is not None and from_time >= to_time:
        raise HTTPException(status_code=422, detail="'from' must be earlier than 'to'")
    if year is not None and (from_time is not None or to_time is not None):
        raise HTTPException(status_code=422, detail="'year' cannot be combined with 'from' or 'to'")
    try:
        zone = ZoneInfo(site.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid site timezone: {site.timezone}") from exc
    if year is not None:
        from_time = datetime(year, 1, 1, tzinfo=zone).astimezone(UTC)
        to_time = datetime(year + 1, 1, 1, tzinfo=zone).astimezone(UTC)

    peaks = await reading_repo.list_peaks(
        site_id=site.id,
        period=period,
        timezone=site.timezone,
        from_time=from_time,
        to_time=to_time,
    )
    return PeaksResponse(
        slug=slug,
        timezone=site.timezone,
        period=period,
        peaks=[
            PeakReadingResponse(
                period_start=peak.period_start,
                solar_production_w=peak.solar_production_w,
                consumption_w=peak.consumption_w,
                battery_charge_w=peak.battery_charge_w,
                battery_discharge_w=peak.battery_discharge_w,
            )
            for peak in peaks
        ],
    )


@router.get("/sites/{slug}/readings", response_model=HistoryResponse)
async def get_site_readings(
    slug: str,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    bucket: int | None = Query(default=None, ge=1, le=1440),
    site_repo: SiteRepository = Depends(get_site_repository),
    reading_repo: EnergyReadingRepository = Depends(get_reading_repository),
) -> HistoryResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    if from_time is None:
        from_time = datetime.now(UTC) - timedelta(hours=24)
    if to_time is None:
        to_time = datetime.now(UTC)

    if bucket is not None:
        aggregated = await reading_repo.list_aggregated(
            site_id=site.id,
            bucket_minutes=bucket,
            from_time=from_time,
            to_time=to_time,
        )
        return HistoryResponse(
            slug=slug,
            bucket_minutes=bucket,
            readings=[
                AggregatedReadingResponse(
                    bucket_start=r.bucket_start,
                    solar_production_w=r.solar_production_w,
                    consumption_w=r.consumption_w,
                    grid_import_w=r.grid_import_w,
                    grid_export_w=r.grid_export_w,
                    battery_soc_pct=r.battery_soc_pct,
                    battery_power_w=r.battery_power_w,
                )
                for r in aggregated
            ],
        )

    readings = await reading_repo.list_readings(
        site_id=site.id,
        from_time=from_time,
        to_time=to_time,
    )
    return HistoryResponse(
        slug=slug,
        bucket_minutes=0,
        readings=[
            ReadingResponse(
                recorded_at=r.recorded_at,
                solar_production_w=r.solar_production_w,
                consumption_w=r.consumption_w,
                grid_import_w=r.grid_import_w,
                grid_export_w=r.grid_export_w,
                battery_soc_pct=r.battery_soc_pct,
                battery_power_w=r.battery_power_w,
            )
            for r in readings
        ],
    )
