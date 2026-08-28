"""Solar forecast API routes."""



from __future__ import annotations



from datetime import UTC, datetime, timedelta



from app.deps import get_app_settings, get_db_session

from app.schemas import (

    SolarAccuracyResponse,

    SolarDiagnosticsResponse,

    SolarEnergyBudgetResponse,

    SolarForecastObservationResponse,

    SolarForecastPointResponse,

    SolarForecastResponse,

    SolarSiteConfigResponse,

    SolarSiteConfigUpdate,

    SolarWeatherHourResponse,

    SolarWeatherResponse,

)

from energy_core.db.repositories import EnergyReadingRepository, SiteRepository

from energy_core.db.solar_forecast_repo import (

    SolarForecastModelProfileRepository,

    SolarForecastObservationRepository,

    SolarForecastRepository,

    SolarSiteConfigRepository,

)

from energy_core.solar_forecast.budget import ConsumptionForecastProvider, SolarEnergyBudgetService

from energy_core.solar_forecast.calibration import metrics_insufficient

from energy_core.solar_forecast.coordinator import SolarForecastCoordinator

from energy_core.solar_forecast.historical import count_production_days

from energy_core.solar_forecast.types import MODEL_VERSION, ModelState, confidence_label_from_score

from energy_core.solar_forecast.weather_conditions import (

    build_current_weather,

    describe_weather_code,

    hourly_weather_series,

)

from energy_core.solar_intelligence.geometry import SolarGeometryService

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from zoneinfo import ZoneInfo



router = APIRouter(tags=["solar-forecast"])





async def _ensure_solar_observations_evaluated(session: AsyncSession, site, settings) -> None:

    coordinator = SolarForecastCoordinator(settings)

    await coordinator.evaluate_site_observations(session, site, now=datetime.now(UTC))

    await session.flush()





async def _production_days_observed(session: AsyncSession, site, settings, *, now: datetime) -> int:

    window_days = settings.solar_forecast_rolling_window_days

    since = now - timedelta(days=window_days + 2)

    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)

    readings = await reading_repo.list_readings(site.id, from_time=since, to_time=now, limit=100000)

    raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]

    return count_production_days(

        raw,

        timezone=site.timezone,

        window_days=window_days,

        now=now,

    )





async def _resolve_forecast(session: AsyncSession, site, settings):

    config_repo = SolarSiteConfigRepository(session)

    record = await config_repo.get(site.id, timezone=site.timezone)



    if record is None or not record.enabled:

        raise HTTPException(

            status_code=404,

            detail=(

                "Solprognos är inte aktiverad. Gå till Inställningar → Anläggningar, "

                "fyll i koordinater och kWp, och aktivera prognosen."

            ),

        )



    if (

        record.latitude is None

        or record.longitude is None

        or record.installed_peak_power_kw is None

        or record.installed_peak_power_kw <= 0

    ):

        raise HTTPException(

            status_code=404,

            detail=(

                "Solprofilen är ofullständig. Ange latitud, longitud och installerad effekt (kWp) "

                "under Inställningar → Anläggningar."

            ),

        )



    forecast_repo = SolarForecastRepository(session)

    forecast = await forecast_repo.get_latest(site.id)

    if forecast is not None:

        return forecast



    coordinator = SolarForecastCoordinator(settings)

    refreshed = await coordinator.refresh_site_now(session, site)

    if refreshed:

        await session.flush()

        forecast = await forecast_repo.get_latest(site.id)

        if forecast is not None:

            return forecast



    raise HTTPException(

        status_code=503,

        detail="Prognosen kunde inte genereras just nu. Försök igen om en minut.",

    )





async def _forecast_response(session, site, forecast, settings) -> SolarForecastResponse:

    from energy_core.solar_forecast.day_metrics import compute_solar_day_metrics, compute_tomorrow_kwh
    from energy_core.solar_forecast.historical import actual_solar_kwh_today_from_readings

    now = datetime.now(UTC)
    day_metrics = compute_solar_day_metrics(forecast, timezone=site.timezone, now=now)
    forecast_so_far_kwh = day_metrics.forecast_so_far_kwh
    expected_tomorrow_kwh = compute_tomorrow_kwh(forecast, timezone=site.timezone, now=now)

    from zoneinfo import ZoneInfo
    from datetime import time

    tz = ZoneInfo(site.timezone)
    day_start = datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz).astimezone(UTC)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    readings = await reading_repo.list_readings(site.id, from_time=day_start, to_time=now, limit=50000)
    actual_today_kwh = actual_solar_kwh_today_from_readings(
        [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings],
        timezone=site.timezone,
        now=now,
    )
    remaining_vs_expected_kwh = round(
        max(0.0, day_metrics.expected_today_kwh - actual_today_kwh),
        3,
    )



    model_profile_repo = SolarForecastModelProfileRepository(session)

    model_profile = await model_profile_repo.get(site.id)



    production_days = await _production_days_observed(session, site, settings, now=now)



    conf_score = getattr(forecast, "confidence_score", None) or model_profile.confidence_score

    conf_label = confidence_label_from_score(conf_score)

    model_state = getattr(forecast, "model_state", model_profile.model_state)

    if isinstance(model_state, ModelState):

        model_state = model_state.value



    return SolarForecastResponse(

        site_id=forecast.site_id,

        generated_at=forecast.generated_at,

        model_version=forecast.model_version,

        quality=forecast.quality,

        weather_source=forecast.weather_source,

        expected_today_kwh=day_metrics.expected_today_kwh,

        remaining_today_kwh=day_metrics.remaining_today_kwh,

        expected_tomorrow_kwh=expected_tomorrow_kwh,

        peak_power_w=day_metrics.peak_power_w,

        peak_time=day_metrics.peak_time,

        confidence=forecast.confidence,

        lower_today_kwh=forecast.lower_today_kwh,

        upper_today_kwh=forecast.upper_today_kwh,

        weather_summary=forecast.weather_summary,

        actual_today_kwh=actual_today_kwh,

        forecast_so_far_kwh=forecast_so_far_kwh,

        remaining_vs_expected_kwh=remaining_vs_expected_kwh,

        raw_forecast_today_kwh=getattr(forecast, "raw_forecast_today_kwh", forecast.expected_today_kwh),

        raw_forecast_so_far_kwh=day_metrics.raw_forecast_so_far_kwh,

        raw_forecast_tomorrow_kwh=getattr(forecast, "raw_forecast_tomorrow_kwh", expected_tomorrow_kwh),

        corrected_forecast_today_kwh=getattr(forecast, "corrected_forecast_today_kwh", forecast.expected_today_kwh),

        corrected_forecast_tomorrow_kwh=getattr(

            forecast, "corrected_forecast_tomorrow_kwh", expected_tomorrow_kwh

        ),

        correction_factor=getattr(forecast, "correction_factor", model_profile.correction_factor),

        model_state=str(model_state),

        confidence_score=conf_score,

        confidence_label=conf_label,

        historical_samples=getattr(forecast, "historical_samples", model_profile.historical_samples),

        production_days_observed=production_days,

        points=[

            SolarForecastPointResponse(

                timestamp=p.timestamp,

                baseline_power_w=p.baseline_power_w,

                corrected_power_w=p.corrected_power_w,

                expected_energy_kwh=p.expected_energy_kwh,

                lower_bound_power_w=p.lower_bound_power_w,

                upper_bound_power_w=p.upper_bound_power_w,

                confidence=p.confidence,

                correction_factor=p.correction_factor,

            )

            for p in forecast.points

        ],

    )





@router.get("/sites/{slug}/solar/config", response_model=SolarSiteConfigResponse)

async def get_solar_config(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

) -> SolarSiteConfigResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    row = await SolarSiteConfigRepository(session).get(site.id, timezone=site.timezone)

    if row is None:

        return SolarSiteConfigResponse(site_slug=slug, enabled=False, complete=False)

    complete = (

        row.latitude is not None

        and row.longitude is not None

        and row.installed_peak_power_kw is not None

        and row.installed_peak_power_kw > 0

        and row.enabled

    )

    return SolarSiteConfigResponse(

        site_slug=slug,

        latitude=row.latitude,

        longitude=row.longitude,

        installed_peak_power_kw=row.installed_peak_power_kw,

        azimuth_deg=row.azimuth_deg,

        tilt_deg=row.tilt_deg,

        inverter_max_power_kw=row.inverter_max_power_kw,

        system_loss_percent=row.system_loss_percent,

        enabled=row.enabled,

        tilt_estimated=row.tilt_estimated,

        azimuth_estimated=row.azimuth_estimated,

        complete=complete,

        solar_intelligence_enabled=getattr(row, "solar_intelligence_enabled", False),

    )





@router.put("/sites/{slug}/solar/config", response_model=SolarSiteConfigResponse)

async def update_solar_config(

    slug: str,

    payload: SolarSiteConfigUpdate,

    session: AsyncSession = Depends(get_db_session),

    settings=Depends(get_app_settings),

) -> SolarSiteConfigResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")



    if payload.enabled:

        if payload.latitude is None or payload.longitude is None or payload.installed_peak_power_kw is None:

            raise HTTPException(

                status_code=422,

                detail="latitude, longitude and installed_peak_power_kw required to enable forecast",

            )

        if not (-90 <= payload.latitude <= 90):

            raise HTTPException(status_code=422, detail="latitude must be between -90 and 90")

        if not (-180 <= payload.longitude <= 180):

            raise HTTPException(status_code=422, detail="longitude must be between -180 and 180")

        if payload.installed_peak_power_kw <= 0:

            raise HTTPException(status_code=422, detail="installed_peak_power_kw must be positive")



    repo = SolarSiteConfigRepository(session)

    existing = await repo.get(site.id, timezone=site.timezone)

    significant = False

    if existing:

        for field, new_val in (

            ("installed_peak_power_kw", payload.installed_peak_power_kw),

            ("azimuth_deg", payload.azimuth_deg),

            ("tilt_deg", payload.tilt_deg),

            ("inverter_max_power_kw", payload.inverter_max_power_kw),

        ):

            if new_val is not None and getattr(existing, field) != new_val:

                significant = True

                break



    await repo.upsert(

        site.id,

        latitude=payload.latitude,

        longitude=payload.longitude,

        installed_peak_power_kw=payload.installed_peak_power_kw,

        azimuth_deg=payload.azimuth_deg,

        tilt_deg=payload.tilt_deg,

        inverter_max_power_kw=payload.inverter_max_power_kw,

        system_loss_percent=payload.system_loss_percent,

        enabled=payload.enabled,

        tilt_estimated=payload.tilt_estimated,

        azimuth_estimated=payload.azimuth_estimated,

        solar_intelligence_enabled=payload.solar_intelligence_enabled,

    )

    await repo.bump_configuration_version(

        site.id,

        payload.model_dump(),

        significant_change=significant,

    )

    await session.commit()



    coordinator = SolarForecastCoordinator(settings)

    await coordinator.refresh_site_now(session, site)

    await session.commit()



    return await get_solar_config(slug, session)





@router.get("/sites/{slug}/solar/forecast", response_model=SolarForecastResponse)

async def get_solar_forecast(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

    settings=Depends(get_app_settings),

) -> SolarForecastResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    forecast = await _resolve_forecast(session, site, settings)

    return await _forecast_response(session, site, forecast, settings)





@router.get("/sites/{slug}/solar/forecast/today", response_model=SolarForecastResponse)

async def get_solar_forecast_today(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

    settings=Depends(get_app_settings),

) -> SolarForecastResponse:

    return await get_solar_forecast(slug, session, settings)





@router.get("/sites/{slug}/solar/forecast/tomorrow", response_model=SolarForecastResponse)

async def get_solar_forecast_tomorrow(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

    settings=Depends(get_app_settings),

) -> SolarForecastResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    forecast = await _resolve_forecast(session, site, settings)

    return await _forecast_response(session, site, forecast, settings)





@router.get("/sites/{slug}/solar/accuracy", response_model=SolarAccuracyResponse)

async def get_solar_accuracy(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

    settings=Depends(get_app_settings),

) -> SolarAccuracyResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    profile_repo = SolarForecastModelProfileRepository(session)

    profile = await profile_repo.get(site.id)

    insufficient = metrics_insufficient(profile, settings)

    production_days = await _production_days_observed(session, site, settings, now=datetime.now(UTC))



    return SolarAccuracyResponse(

        site_slug=slug,

        model_version=profile.model_version or MODEL_VERSION,

        model_state=profile.model_state.value,

        mape_7d_pct=None if insufficient else profile.mape_7d,

        mape_30d_pct=None if insufficient else profile.mape_30d,

        mape_7d_valid_days=profile.mape_7d_valid_days,

        mape_30d_valid_days=profile.mape_30d_valid_days,

        mae_kwh_7d=None if insufficient else profile.mae_7d,

        mae_kwh_30d=None if insufficient else profile.mae_30d,

        bias_pct_30d=None if insufficient else profile.bias_30d,

        sample_count_30d=profile.historical_samples,

        historical_samples=profile.historical_samples,

        production_days_observed=production_days,

        correction_factor=profile.correction_factor,

        confidence_score=None if insufficient else profile.confidence_score,

        confidence_label=confidence_label_from_score(None if insufficient else profile.confidence_score),

        metrics_insufficient=insufficient,

        raw_mae_30d=None if insufficient else profile.raw_mae_30d,

        corrected_mae_30d=None if insufficient else profile.corrected_mae_30d,

        improvement_pct_30d=None if insufficient else profile.improvement_pct_30d,

        wape_7d_pct=None if insufficient else profile.wape_7d,

        wape_30d_pct=None if insufficient else profile.wape_30d,

        rmse_kwh_7d=None if insufficient else profile.rmse_7d,

        rmse_kwh_30d=None if insufficient else profile.rmse_30d,

        r2_30d=None if insufficient else profile.r2_30d,

        insufficient_reason=(
            "no_training_samples"
            if profile.historical_samples <= 0
            else "model_learning"
            if profile.model_state.value in ("NO_DATA", "LEARNING")
            else "insufficient_samples"
            if insufficient
            else None
        ),

        min_samples_for_calibrated=settings.solar_forecast_min_samples_calibrated,

    )





@router.get("/sites/{slug}/solar/diagnostics", response_model=SolarDiagnosticsResponse)

async def get_solar_diagnostics(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

    limit: int = 60,

) -> SolarDiagnosticsResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")



    obs_repo = SolarForecastObservationRepository(session)

    observations = await obs_repo.list_for_site(site.id, limit=limit)

    return SolarDiagnosticsResponse(

        site_slug=slug,

        observations=[

            SolarForecastObservationResponse(

                forecast_date=o.forecast_date,

                forecast_kwh_raw=o.forecast_kwh_raw,

                forecast_kwh_corrected=o.forecast_kwh_corrected,

                actual_kwh=o.actual_kwh,

                absolute_error_kwh=o.absolute_error_kwh,

                raw_absolute_error_kwh=o.raw_absolute_error_kwh,

                percentage_error=o.percentage_error,

                data_completeness_pct=o.data_completeness_pct,

                correction_factor_used=o.correction_factor_used,

                weather_condition_bucket=o.weather_condition_bucket,

                training_eligible=o.training_eligible,

                exclusion_reason=o.exclusion_reason,

                model_version=o.model_version,

            )

            for o in observations

        ],

    )





@router.get("/sites/{slug}/solar/energy-budget", response_model=SolarEnergyBudgetResponse)

async def get_solar_energy_budget(

    slug: str,

    session: AsyncSession = Depends(get_db_session),

    settings=Depends(get_app_settings),

) -> SolarEnergyBudgetResponse:

    site = await SiteRepository(session).get_by_slug(slug)

    if site is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")



    forecast = await _resolve_forecast(session, site, settings)



    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)

    since = datetime.now(UTC) - timedelta(days=14)

    readings = await reading_repo.list_readings(site.id, from_time=since, limit=50000)

    raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]

    consumption = ConsumptionForecastProvider().forecast_remaining_today(

        raw, timezone=site.timezone, now=datetime.now(UTC)

    )



    budget = SolarEnergyBudgetService().compute(

        forecast,

        consumption_forecast=consumption,

    )

    return SolarEnergyBudgetResponse(

        site_slug=slug,

        forecast_solar_kwh=budget.forecast_solar_kwh,

        expected_house_consumption_kwh=budget.expected_house_consumption_kwh,

        expected_surplus_kwh=budget.expected_surplus_kwh,

        expected_deficit_kwh=budget.expected_deficit_kwh,

        confidence=budget.confidence,

        quality=budget.quality,

        consumption_source=budget.consumption_source,

    )


@router.get("/sites/{slug}/solar/weather", response_model=SolarWeatherResponse)
async def get_solar_weather(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> SolarWeatherResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    config_repo = SolarSiteConfigRepository(session)
    config = await config_repo.get(site.id, timezone=site.timezone)
    if config is None or not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Väderprognos kräver att solprognosen är aktiverad för anläggningen.",
        )
    if config.latitude is None or config.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ange latitud och longitud för anläggningen för att visa väderprognos.",
        )

    now = datetime.now(UTC)
    coordinator = SolarForecastCoordinator(settings)
    resolved = await coordinator.resolve_weather(session, site, now=now)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Väderdata kunde inte hämtas just nu.",
        )
    await session.commit()

    weather, source, cache_age = resolved
    current = build_current_weather(weather, now=now)
    hourly = hourly_weather_series(weather, now=now, hours=24)

    forecast_by_hour: dict[datetime, float] = {}
    try:
        forecast = await _resolve_forecast(session, site, settings)
    except HTTPException:
        forecast = None
    if forecast is not None:
        for point in forecast.points:
            hour = point.timestamp.replace(minute=0, second=0, microsecond=0)
            forecast_by_hour.setdefault(hour, point.corrected_power_w)

    geometry = SolarGeometryService(
        latitude=config.latitude,
        longitude=config.longitude,
        timezone=site.timezone,
    )
    sunrise, sunset = geometry.sunrise_sunset(now.astimezone(ZoneInfo(site.timezone)).date())

    return SolarWeatherResponse(
        site_slug=slug,
        provider=weather.provider,
        source=source,
        fetched_at=weather.fetched_at,
        cache_age_minutes=round(cache_age, 1),
        sunrise=sunrise,
        sunset=sunset,
        current=_weather_hour_response(current) if current else None,
        solar_impact_sv=current.solar_impact_sv if current else "",
        hours=[
            _weather_point_response(point, forecast_by_hour.get(point.timestamp.replace(minute=0, second=0, microsecond=0)))
            for point in hourly
        ],
    )


def _weather_hour_response(current) -> SolarWeatherHourResponse:
    return SolarWeatherHourResponse(
        timestamp=current.timestamp,
        temperature_c=current.temperature_c,
        cloud_cover_pct=current.cloud_cover_pct,
        wind_speed_ms=current.wind_speed_ms,
        relative_humidity_pct=current.relative_humidity_pct,
        precipitation_mm=current.precipitation_mm,
        ghi_wm2=current.ghi_wm2,
        weather_code=current.weather_code,
        condition_sv=current.condition_sv,
        condition_icon=current.condition_icon,
    )


def _weather_point_response(point, forecast_power_w: float | None) -> SolarWeatherHourResponse:
    label, icon = describe_weather_code(point.weather_code, point.cloud_cover_pct)
    return SolarWeatherHourResponse(
        timestamp=point.timestamp,
        temperature_c=_round_or_none(point.temperature_c, 1),
        cloud_cover_pct=_round_or_none(point.cloud_cover_pct, 0),
        wind_speed_ms=_round_or_none(point.wind_speed_ms, 1),
        relative_humidity_pct=_round_or_none(point.relative_humidity_pct, 0),
        precipitation_mm=_round_or_none(point.precipitation_mm, 1),
        ghi_wm2=_round_or_none(point.ghi_wm2, 0),
        weather_code=point.weather_code,
        condition_sv=label,
        condition_icon=icon,
        forecast_power_w=_round_or_none(forecast_power_w, 0),
    )


def _round_or_none(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits) if digits > 0 else float(round(value))


