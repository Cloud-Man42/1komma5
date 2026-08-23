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
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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

    from energy_core.solar_forecast.historical import actual_solar_kwh_today_from_readings

    now = datetime.now(UTC)

    forecast_so_far_kwh = round(
        max(0.0, forecast.expected_today_kwh - forecast.remaining_today_kwh),
        3,
    )

    from datetime import time
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(site.timezone)

    day_start = datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz).astimezone(UTC)

    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)

    readings = await reading_repo.list_readings(
        site.id, from_time=day_start, to_time=now, limit=50000
    )

    actual_today_kwh = actual_solar_kwh_today_from_readings(
        [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings],
        timezone=site.timezone,
        now=now,
    )

    remaining_vs_expected_kwh = round(
        max(0.0, forecast.expected_today_kwh - actual_today_kwh),
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
        expected_today_kwh=forecast.expected_today_kwh,
        remaining_today_kwh=forecast.remaining_today_kwh,
        expected_tomorrow_kwh=forecast.expected_tomorrow_kwh,
        peak_power_w=forecast.peak_power_w,
        peak_time=forecast.peak_time,
        confidence=forecast.confidence,
        lower_today_kwh=forecast.lower_today_kwh,
        upper_today_kwh=forecast.upper_today_kwh,
        weather_summary=forecast.weather_summary,
        actual_today_kwh=actual_today_kwh,
        forecast_so_far_kwh=forecast_so_far_kwh,
        remaining_vs_expected_kwh=remaining_vs_expected_kwh,
        raw_forecast_today_kwh=getattr(
            forecast, "raw_forecast_today_kwh", forecast.expected_today_kwh
        ),
        raw_forecast_tomorrow_kwh=getattr(
            forecast, "raw_forecast_tomorrow_kwh", forecast.expected_tomorrow_kwh
        ),
        corrected_forecast_today_kwh=getattr(
            forecast, "corrected_forecast_today_kwh", forecast.expected_today_kwh
        ),
        corrected_forecast_tomorrow_kwh=getattr(
            forecast, "corrected_forecast_tomorrow_kwh", forecast.expected_tomorrow_kwh
        ),
        correction_factor=getattr(forecast, "correction_factor", model_profile.correction_factor),
        model_state=str(model_state),
        confidence_score=conf_score,
        confidence_label=conf_label,
        historical_samples=getattr(
            forecast, "historical_samples", model_profile.historical_samples
        ),
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
        if (
            payload.latitude is None
            or payload.longitude is None
            or payload.installed_peak_power_kw is None
        ):
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

    await _ensure_solar_observations_evaluated(session, site, settings)

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

    await _ensure_solar_observations_evaluated(session, site, settings)

    profile_repo = SolarForecastModelProfileRepository(session)

    profile = await profile_repo.get(site.id)

    insufficient = metrics_insufficient(profile, settings)

    production_days = await _production_days_observed(
        session, site, settings, now=datetime.now(UTC)
    )

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
        confidence_label=confidence_label_from_score(
            None if insufficient else profile.confidence_score
        ),
        metrics_insufficient=insufficient,
        raw_mae_30d=None if insufficient else profile.raw_mae_30d,
        corrected_mae_30d=None if insufficient else profile.corrected_mae_30d,
        improvement_pct_30d=None if insufficient else profile.improvement_pct_30d,
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
