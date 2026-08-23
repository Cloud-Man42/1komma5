"""Solar forecast coordinator — refresh, evaluate, profile updates."""



from __future__ import annotations



import logging

from datetime import UTC, date, datetime, timedelta



from sqlalchemy.ext.asyncio import AsyncSession



from energy_core.config import Settings, get_settings

from energy_core.db.repositories import EnergyReadingRepository

from energy_core.db.solar_forecast_repo import (

    SolarArrayRepository,

    SolarEvaluationRepository,

    SolarForecastModelProfileRepository,

    SolarForecastObservationRepository,

    SolarForecastRepository,

    SolarPerformanceProfileRepository,

    SolarSiteConfigRepository,

    SolarWeatherCacheRepository,

    _to_domain_config,

)

from energy_core.solar_forecast.accuracy import EvaluationInput, evaluate_point

from energy_core.solar_forecast.correction import build_profile

from energy_core.solar_forecast.daily_evaluation import (

    actual_kwh_for_day,

    build_forecast_observation_stub,

    build_observation_from_day,

    days_in_evaluation_window,

    forecast_kwh_for_day,

    recompute_profile_from_observations,

)

from energy_core.solar_forecast.engine import SolarForecastEngine

from energy_core.solar_forecast.historical import (

    actual_energy_kwh,

    aggregate_buckets_from_readings,

    build_performance_sample,

    coverage_fraction,

    floor_15min,

)

from energy_core.solar_forecast.open_meteo import (

    OpenMeteoWeatherProvider,

    WeatherProviderError,

)

from energy_core.solar_forecast.physical import baseline_energy_kwh, baseline_power_w

from energy_core.solar_forecast.types import PerformanceSample, WeatherForecast



logger = logging.getLogger(__name__)





class SolarForecastCoordinator:

    """Runs forecast refresh, evaluation and profile learning per site."""



    def __init__(self, settings: Settings | None = None) -> None:

        self._settings = settings or get_settings()

        self._engine = SolarForecastEngine(horizon_hours=self._settings.solar_forecast_horizon_hours)

        self._provider = OpenMeteoWeatherProvider(

            base_url=self._settings.open_meteo_base_url,

            historical_url=self._settings.open_meteo_historical_url,

            api_key=self._settings.open_meteo_api_key or None,

            timeout_seconds=self._settings.open_meteo_timeout_seconds,

        )

        self._last_refresh: dict[int, datetime] = {}

        self._last_eval: dict[int, datetime] = {}

        self._last_daily_eval: dict[int, date] = {}



    async def run_due_sites(self, session: AsyncSession, sites: list) -> int:

        now = datetime.now(UTC)

        processed = 0

        for site in sites:

            try:

                if await self._refresh_site_if_due(session, site, now=now):

                    processed += 1

                await self._evaluate_daily_observations(session, site, now=now)

                await self._evaluate_site_if_due(session, site, now=now)

            except Exception:

                logger.exception("Solar forecast failed for site %s", site.slug)

        return processed



    async def refresh_site_now(self, session: AsyncSession, site) -> bool:

        return await self._refresh_site_if_due(session, site, now=datetime.now(UTC), force=True)



    async def _refresh_site_if_due(

        self,

        session: AsyncSession,

        site,

        *,

        now: datetime,

        force: bool = False,

    ) -> bool:

        config_repo = SolarSiteConfigRepository(session)

        record = await config_repo.get(site.id, timezone=site.timezone)

        if record is None or not record.enabled:

            return False

        if record.latitude is None or record.longitude is None or not record.installed_peak_power_kw:

            return False



        last = self._last_refresh.get(site.id)

        interval = timedelta(minutes=self._settings.solar_forecast_refresh_minutes)

        if not force and last and now - last < interval:

            return False



        domain = _to_domain_config(record)

        if not domain.is_complete():

            return False



        array_repo = SolarArrayRepository(session)

        await array_repo.ensure_default_for_site(site.id, domain)



        weather, source, cache_age = await self._fetch_weather(session, domain, now=now)

        profile_repo = SolarPerformanceProfileRepository(session)

        profile = await profile_repo.get(site.id)



        samples = await self._collect_samples(session, site, domain, now=now)

        if samples:

            learned = build_profile(samples, now=now)

            profile = learned.__class__(

                site_id=site.id,

                global_factor=learned.global_factor,

                seasonal_factors=learned.seasonal_factors,

                hour_factors=learned.hour_factors,

                weather_factors=learned.weather_factors,

                sample_count=learned.sample_count,

                mape_7d=profile.mape_7d,

                mape_30d=profile.mape_30d,

                mae_kwh_30d=profile.mae_kwh_30d,

                bias_pct_30d=profile.bias_pct_30d,

                updated_at=now,

            )



        model_profile_repo = SolarForecastModelProfileRepository(session)

        model_profile = await model_profile_repo.get(site.id)

        config_version = await config_repo.get_configuration_version(site.id)



        forecast = self._engine.generate(

            domain,

            weather,

            profile,

            now=now,

            weather_source=source,

            cache_age_minutes=cache_age,

            model_profile=model_profile,

        )



        forecast_repo = SolarForecastRepository(session)

        await forecast_repo.save_run(forecast)

        await config_repo.touch_forecast(site.id)



        obs_repo = SolarForecastObservationRepository(session)

        from zoneinfo import ZoneInfo



        tz = ZoneInfo(site.timezone)

        local_tomorrow = now.astimezone(tz).date() + timedelta(days=1)

        stub = build_forecast_observation_stub(

            site.id,

            local_tomorrow,

            forecast=forecast,

            timezone=site.timezone,

            correction_factor_used=model_profile.correction_factor,

            site_configuration_version=config_version,

        )

        await obs_repo.upsert(stub)

        logger.info(

            "Solar forecast generated site_id=%s date=%s raw=%.2f corrected=%.2f",

            site.id,

            local_tomorrow,

            stub.forecast_kwh_raw or 0,

            stub.forecast_kwh_corrected or 0,

        )



        retention = now - timedelta(days=self._settings.solar_forecast_retention_days)

        await forecast_repo.prune_runs(site.id, keep_after=retention)



        cache_repo = SolarWeatherCacheRepository(session)

        await cache_repo.prune_old(site.id, keep_after=retention)



        self._last_refresh[site.id] = now

        return True



    async def evaluate_site_observations(self, session, site, *, now: datetime | None = None) -> None:

        await self._evaluate_daily_observations(session, site, now=now or datetime.now(UTC))



    async def _evaluate_daily_observations(self, session, site, *, now: datetime) -> None:

        from zoneinfo import ZoneInfo



        local_today = now.astimezone(ZoneInfo(site.timezone)).date()

        config_repo = SolarSiteConfigRepository(session)

        record = await config_repo.get(site.id, timezone=site.timezone)

        if record is None or not record.enabled:

            return



        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)

        window_days = self._settings.solar_forecast_rolling_window_days

        since = now - timedelta(days=window_days + 2)

        readings = await reading_repo.list_readings(site.id, from_time=since, to_time=now, limit=100000)

        raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]



        forecast_repo = SolarForecastRepository(session)

        latest_forecast = await forecast_repo.get_latest(site.id)

        obs_repo = SolarForecastObservationRepository(session)

        config_version = await config_repo.get_configuration_version(site.id)

        model_profile_repo = SolarForecastModelProfileRepository(session)

        previous_profile = await model_profile_repo.get(site.id)



        pending_days: list = []

        for day in days_in_evaluation_window(site.timezone, now=now, window_days=window_days):

            existing = await obs_repo.get(site.id, day)

            if existing is not None and existing.actual_kwh is not None:

                continue

            pending_days.append(day)



        if not pending_days:

            last_eval = self._last_daily_eval.get(site.id)

            if last_eval == local_today:

                return



        for day in pending_days:

            actual_kwh, completeness = actual_kwh_for_day(raw, day, site.timezone)

            if completeness <= 0 and actual_kwh <= 0:

                continue



            day_forecast = latest_forecast

            if day_forecast is not None:

                raw_kwh, corrected_kwh = forecast_kwh_for_day(day_forecast, day, site.timezone)

                if raw_kwh <= 0 and corrected_kwh <= 0:

                    day_forecast = None



            observation = build_observation_from_day(

                site.id,

                day,

                forecast=day_forecast,

                actual_kwh=actual_kwh,

                data_completeness_pct=completeness,

                timezone=site.timezone,

                correction_factor_used=previous_profile.correction_factor,

                site_configuration_version=config_version,

                settings=self._settings,

            )

            await obs_repo.upsert(observation)

            if not observation.training_eligible and observation.exclusion_reason:

                logger.info(

                    "Observation excluded site_id=%s date=%s reason=%s",

                    site.id,

                    day,

                    observation.exclusion_reason,

                )

            else:

                logger.info(

                    "Solar forecast evaluated site_id=%s date=%s actual=%.2f corrected=%.2f",

                    site.id,

                    day,

                    actual_kwh,

                    observation.forecast_kwh_corrected or 0,

                )



        all_obs = await obs_repo.list_for_site(site.id, limit=window_days + 5)

        updated_profile = recompute_profile_from_observations(

            site.id,

            all_obs,

            previous=previous_profile,

            now=now,

            settings=self._settings,

        )

        await model_profile_repo.save(updated_profile)

        self._last_daily_eval[site.id] = local_today



    async def _fetch_weather(

        self,

        session: AsyncSession,

        site_config,

        *,

        now: datetime,

    ) -> tuple[WeatherForecast, str, float]:

        cache_repo = SolarWeatherCacheRepository(session)

        cached = await cache_repo.get_latest_valid(site_config.site_id, now=now)

        if cached:

            age = (now - cached.fetched_at).total_seconds() / 60.0

            return cached, "cache", age



        from_ts = now

        to_ts = now + timedelta(hours=self._settings.solar_forecast_horizon_hours)

        try:

            weather = await self._provider.get_forecast(site_config, from_ts, to_ts)

            valid_until = now + timedelta(minutes=self._settings.solar_weather_cache_minutes)

            await cache_repo.save(weather, valid_until=valid_until)

            return weather, "live", 0.0

        except WeatherProviderError:

            logger.warning("Weather provider failed for site %s, trying cache/fallback", site_config.site_id)

            if cached:

                age = (now - cached.fetched_at).total_seconds() / 60.0

                if age <= self._settings.solar_weather_stale_minutes:

                    return cached, "cache", age

            return self._fallback_weather(site_config, now), "fallback", 999.0



    def _fallback_weather(self, site_config, now: datetime) -> WeatherForecast:

        """Minimal diurnal fallback when API unavailable."""

        from energy_core.solar_forecast.types import WeatherForecastPoint



        points = []

        for i in range(self._settings.solar_forecast_horizon_hours * 4):

            ts = now + timedelta(minutes=15 * i)

            hour = ts.hour

            ghi = max(0.0, 800.0 * _diurnal(hour))

            points.append(

                WeatherForecastPoint(

                    timestamp=ts,

                    ghi_wm2=ghi,

                    gti_wm2=ghi * 0.9,

                    cloud_cover_pct=50.0,

                    temperature_c=15.0,

                )

            )

        return WeatherForecast(

            site_id=site_config.site_id,

            fetched_at=now,

            provider="fallback",

            points=tuple(points),

            source="fallback",

        )



    async def _collect_samples(self, session, site, domain, *, now: datetime) -> list[PerformanceSample]:

        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)

        since = now - timedelta(days=30)

        readings = await reading_repo.list_readings(site.id, from_time=since, to_time=now, limit=50000)

        if not readings:

            return []



        raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]

        buckets = aggregate_buckets_from_readings(raw)

        samples: list[PerformanceSample] = []



        for b in buckets:

            from energy_core.solar_forecast.types import WeatherForecastPoint



            wp = WeatherForecastPoint(timestamp=b.bucket_start, ghi_wm2=600.0, gti_wm2=550.0)

            baseline_w = baseline_power_w(wp, domain)

            baseline_kwh = baseline_energy_kwh(baseline_w)

            actual_kwh = actual_energy_kwh(b.avg_solar_w)

            cov = coverage_fraction(b)

            sample = build_performance_sample(

                bucket_start=b.bucket_start,

                actual_kwh=actual_kwh,

                baseline_kwh=baseline_kwh,

                weather=wp,

                coverage=cov,

            )

            if sample:

                samples.append(sample)

        return samples



    async def _evaluate_site_if_due(self, session, site, *, now: datetime) -> None:

        """Legacy 15-min bucket evaluation — kept for chart diagnostics, not v2 metrics."""

        last = self._last_eval.get(site.id)

        if last and now - last < timedelta(minutes=15):

            return



        bucket_start = floor_15min(now) - timedelta(minutes=15)

        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)

        from_ts = bucket_start

        to_ts = bucket_start + timedelta(minutes=15)

        readings = await reading_repo.list_readings(site.id, from_time=from_ts, to_time=to_ts, limit=1000)

        if not readings:

            return



        actual_w = sum(r.solar_production_w for r in readings) / len(readings)

        actual_kwh = actual_energy_kwh(actual_w)



        forecast_repo = SolarForecastRepository(session)

        latest = await forecast_repo.get_latest(site.id)

        if latest is None:

            return



        forecast_kwh = 0.0

        for p in latest.points:

            if p.timestamp == bucket_start:

                forecast_kwh = p.expected_energy_kwh

                break



        if forecast_kwh <= 0 and actual_kwh <= 0:

            return



        eval_repo = SolarEvaluationRepository(session)

        ev = evaluate_point(

            site.id,

            EvaluationInput(

                bucket_start=bucket_start,

                forecasted_energy_kwh=forecast_kwh,

                actual_energy_kwh=actual_kwh,

                model_version=latest.model_version,

            ),

        )

        await eval_repo.upsert(ev)

        self._last_eval[site.id] = now





def _diurnal(hour: int) -> float:

    if hour < 6 or hour > 20:

        return 0.0

    x = (hour - 13) / 4.0

    import math



    return math.exp(-0.5 * x * x)


