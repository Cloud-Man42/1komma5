"""Smart spa energy planning orchestration."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.consumer_repo import ConsumerRepository, ConsumerSampleRepository
from energy_core.db.flexible_load_plan_repo import FlexibleLoadPlanRepository
from energy_core.db.repositories import EnergyReadingRepository, MarketPriceRepository, SiteModel
from energy_core.db.solar_forecast_repo import SolarForecastRepository
from energy_core.db.spa_actuator_repo import SpaActuatorStateRepository
from energy_core.db.spa_control_repo import SpaControlConfigRepository
from energy_core.db.spa_event_repo import SpaEnergyEventRepository
from energy_core.flexible_load.horizon import EnergyHorizonBuilder, HorizonInputs
from energy_core.flexible_load.house_load import HouseLoadForecastProvider
from energy_core.flexible_load.optimizer import FlexibleLoadOptimizer
from energy_core.flexible_load.orchestrator import OrchestratedLoadSpec
from energy_core.flexible_load.types import EnergySource, FlexibleLoad, LoadPlan, LoadStrategy
from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration, SpaPowerProfiles
from energy_core.integrations.arctic_spa.control_service import ArcticSpaControlService
from energy_core.secrets import CredentialCipher
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus
from energy_core.spa_energy.actuator import SpaActuatorDecision, SpaCleaningActuator
from energy_core.spa_energy.filter_policy import SpaFilterPolicy, is_spa_filter_self_managed
from energy_core.spa_energy.filter_schedule_service import ArcticSpaFilterScheduleService
from energy_core.spa_energy.runtime import SpaActuatorRuntime
from energy_core.spa_energy.watchdog import SpaPlannerWatchdog
from energy_core.spa_energy.requirement import (
    build_cleaning_requirement,
    detect_last_cleaning_end,
    window_bounds,
)

logger = logging.getLogger(__name__)

LOAD_ID = "spa_cleaning"


class SmartSpaEnergyService:
    """Plan and optionally actuate optimal spa cleaning windows."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run_cycle(self, session: AsyncSession) -> int:
        from energy_core.site_energy.orchestrator_service import SiteEnergyOrchestratorService

        return await SiteEnergyOrchestratorService(self._settings).run_cycle(session)

    async def run_cleaning_now(self, session: AsyncSession, slug: str) -> SpaActuatorDecision | None:
        repo = ConsumerRepository(session)
        row = await repo.get_spa_by_site_slug(slug)
        if row is None:
            return None
        consumer, device_config, site = row
        control_repo = SpaControlConfigRepository(session)
        control = await control_repo.get_or_create(consumer.id)
        if not control.smart_control_enabled:
            return None
        now = datetime.now(UTC)
        plan = await self._build_plan(session, consumer, device_config, site, control, now)
        return await self._actuate(
            session,
            consumer=consumer,
            device_config=device_config,
            site=site,
            control=control,
            plan=plan,
            now=now,
            manual_override=True,
        )

    async def plan_for_site_slug(self, session: AsyncSession, slug: str) -> bool:
        repo = ConsumerRepository(session)
        row = await repo.get_spa_by_site_slug(slug)
        if row is None:
            return False
        consumer, device_config, site = row
        return await self._plan_for_consumer(session, consumer, device_config, site)

    async def _plan_for_consumer(
        self,
        session: AsyncSession,
        consumer,
        device_config,
        site: SiteModel,
    ) -> bool:
        control_repo = SpaControlConfigRepository(session)
        control = await control_repo.get_or_create(consumer.id)
        if not control.smart_control_enabled and not control.shadow_mode:
            return False

        now = datetime.now(UTC)
        plan = await self._build_plan(session, consumer, device_config, site, control, now)
        dry_run = control.dry_run or control.shadow_mode

        plan_repo = FlexibleLoadPlanRepository(session)
        saved = await plan_repo.save_plan(
            site_id=site.id,
            consumer_id=consumer.id,
            plan=plan,
            dry_run=dry_run,
        )

        event_repo = SpaEnergyEventRepository(session)
        for window in plan.windows:
            await event_repo.insert(
                consumer_id=consumer.id,
                timestamp=now,
                event_type="cleaning_scheduled",
                reason=plan.reason,
                reason_sv=plan.reason_sv,
                strategy=plan.strategy.value,
                start_time=window.start,
                stop_time=window.end,
                runtime_seconds=window.duration.total_seconds(),
                estimated_kwh=window.expected_energy_kwh,
                estimated_cost=window.expected_cost_sek,
                solar_share=self._source_share(window, EnergySource.SOLAR),
                battery_share=self._source_share(window, EnergySource.BATTERY),
                grid_share=self._source_share(window, EnergySource.GRID),
                decision_score=window.average_score,
                dry_run=dry_run,
                shadow=control.shadow_mode,
            )

        if (
            control.smart_control_enabled
            and self._settings.spa_smart_control_enabled
            and not is_spa_filter_self_managed(control)
        ):
            await self._actuate(
                session,
                consumer=consumer,
                device_config=device_config,
                site=site,
                control=control,
                plan=plan,
                now=now,
                manual_override=False,
            )

        logger.debug(
            "Spa plan saved id=%s site=%s reason=%s dry_run=%s",
            saved.id,
            site.slug,
            plan.reason,
            dry_run,
        )
        return True

    async def build_orchestrated_spec(
        self,
        session: AsyncSession,
        consumer,
        device_config,
        site: SiteModel,
    ) -> OrchestratedLoadSpec | None:
        if not self._settings.arctic_spa_enabled:
            return None
        control_repo = SpaControlConfigRepository(session)
        control = await control_repo.get_or_create(consumer.id)
        if not control.smart_control_enabled and not control.shadow_mode:
            return None

        now = datetime.now(UTC)
        load = await self._build_flexible_load(session, consumer, device_config, site, control, now)
        return OrchestratedLoadSpec(
            load=load,
            strategy=LoadStrategy(control.strategy),
            allow_battery=control.allow_battery,
            prefer_solar=control.prefer_solar,
            min_battery_soc_pct=control.min_battery_soc_pct,
            fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        )

    async def apply_orchestrated_plan(
        self,
        session: AsyncSession,
        *,
        consumer,
        device_config,
        site: SiteModel,
        plan: LoadPlan,
        now: datetime,
        manual_override: bool = False,
    ) -> bool:
        control_repo = SpaControlConfigRepository(session)
        control = await control_repo.get_or_create(consumer.id)
        dry_run = control.dry_run or control.shadow_mode

        actuator_repo = SpaActuatorStateRepository(session)
        runtime = await actuator_repo.get_or_create(consumer.id)
        await self._maybe_run_watchdog(
            session,
            consumer=consumer,
            device_config=device_config,
            control=control,
            runtime=runtime,
            now=now,
            dry_run=dry_run,
        )
        runtime.last_planner_run_at = now
        await actuator_repo.save(consumer.id, runtime)

        event_repo = SpaEnergyEventRepository(session)
        for window in plan.windows:
            await event_repo.insert(
                consumer_id=consumer.id,
                timestamp=now,
                event_type="cleaning_scheduled",
                reason=plan.reason,
                reason_sv=plan.reason_sv,
                strategy=plan.strategy.value,
                start_time=window.start,
                stop_time=window.end,
                runtime_seconds=window.duration.total_seconds(),
                estimated_kwh=window.expected_energy_kwh,
                estimated_cost=window.expected_cost_sek,
                solar_share=self._source_share(window, EnergySource.SOLAR),
                battery_share=self._source_share(window, EnergySource.BATTERY),
                grid_share=self._source_share(window, EnergySource.GRID),
                decision_score=window.average_score,
                dry_run=dry_run,
                shadow=control.shadow_mode,
                manual_override=manual_override,
            )

        if (
            control.smart_control_enabled
            and self._settings.spa_smart_control_enabled
            and not (is_spa_filter_self_managed(control) and not manual_override)
        ):
            decision = await self._actuate(
                session,
                consumer=consumer,
                device_config=device_config,
                site=site,
                control=control,
                plan=plan,
                now=now,
                manual_override=manual_override,
            )
            return decision.command_sent
        return True

    async def build_horizon(
        self,
        session: AsyncSession,
        site: SiteModel,
        timezone: str,
        now: datetime,
    ):
        return await self._build_horizon(session, site, timezone, now)

    async def _build_flexible_load(
        self,
        session: AsyncSession,
        consumer,
        device_config,
        site: SiteModel,
        control,
        now: datetime,
    ) -> FlexibleLoad:
        status = self._parse_status(device_config.last_status_json)
        sample_repo = ConsumerSampleRepository(session)
        since = now - timedelta(days=7)
        samples = await sample_repo.list_for_period(consumer.id, start=since, end=now)
        sample_pairs = [(s.recorded_at, s.filter_status) for s in samples]
        last_cleaning = detect_last_cleaning_end(sample_pairs)

        policy = SpaFilterPolicy.from_control(control)
        filter_freq = float(policy.cycles_per_day)
        filter_duration = policy.duration_per_cycle_minutes / 60.0

        requirement = build_cleaning_requirement(
            now=now,
            filter_frequency_per_day=filter_freq,
            filter_duration_hours=filter_duration,
            min_cleaning_hours_per_day=policy.total_daily_runtime_hours,
            last_cleaning_end=last_cleaning,
            timezone=consumer.timezone,
            allowed_window_end_hhmm=control.allowed_window_end,
        )

        earliest, latest = window_bounds(
            now,
            timezone=consumer.timezone,
            start_hhmm=control.allowed_window_start,
            end_hhmm=control.allowed_window_end,
        )

        power_profiles = SpaPowerProfiles.from_json(device_config.power_profiles_json)
        nominal_w = power_profiles.circulation_w + power_profiles.heater_w * 0.3

        min_runtime = timedelta(minutes=policy.duration_per_cycle_minutes)
        daily_target = timedelta(minutes=policy.total_daily_runtime_minutes)

        fixed_start = fixed_end = None
        if control.strategy == "FIXED_SCHEDULE" and control.fixed_schedule_start and control.fixed_schedule_end:
            fixed_start, fixed_end = window_bounds(
                now,
                timezone=consumer.timezone,
                start_hhmm=control.fixed_schedule_start,
                end_hhmm=control.fixed_schedule_end,
            )

        fixed_cycles = policy.cycles_per_day if policy.optimization_enabled else None
        fixed_duration = min_runtime if policy.optimization_enabled else None

        load = FlexibleLoad(
            load_id=LOAD_ID,
            name="Spa filter",
            nominal_power_w=nominal_w,
            minimum_runtime=min_runtime,
            maximum_runtime=daily_target,
            earliest_start=earliest,
            latest_finish=min(latest, requirement.cleaning_deadline),
            deadline=requirement.cleaning_deadline,
            minimum_interval=timedelta(minutes=policy.minimum_cycle_separation_minutes),
            priority=control.load_priority,
            safety_critical=True,
            fixed_start=fixed_start,
            fixed_end=fixed_end,
            daily_runtime_target=daily_target,
            max_starts_per_day=policy.cycles_per_day,
            minimum_pause=timedelta(minutes=policy.minimum_cycle_separation_minutes),
            fixed_cycles_per_day=fixed_cycles,
            fixed_cycle_duration=fixed_duration,
            minimum_cycle_separation=timedelta(minutes=policy.minimum_cycle_separation_minutes),
        )
        return load

    async def _build_plan(
        self,
        session: AsyncSession,
        consumer,
        device_config,
        site: SiteModel,
        control,
        now: datetime,
    ) -> LoadPlan:
        load = await self._build_flexible_load(session, consumer, device_config, site, control, now)
        horizon = await self._build_horizon(session, site, consumer.timezone, now)
        strategy = LoadStrategy(control.strategy)
        optimizer = FlexibleLoadOptimizer(
            allow_battery=control.allow_battery,
            prefer_solar=control.prefer_solar,
            min_battery_soc_pct=control.min_battery_soc_pct,
            fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        )
        return optimizer.plan(load, horizon, strategy, now=now)

    async def _maybe_run_watchdog(
        self,
        session: AsyncSession,
        *,
        consumer,
        device_config,
        control,
        runtime: SpaActuatorRuntime,
        now: datetime,
        dry_run: bool,
    ) -> None:
        if is_spa_filter_self_managed(control):
            return
        cfg = ArcticSpaConfiguration.merge(
            db_enabled=True,
            db_base_url=device_config.api_base_url,
            db_api_key=CredentialCipher().decrypt(device_config.api_key),
            db_spa_id=device_config.external_spa_id,
            db_poll_interval=device_config.poll_interval_seconds,
            db_energy_enabled=device_config.energy_collection_enabled,
            db_cost_enabled=device_config.cost_calculation_enabled,
            db_profiles_json=device_config.power_profiles_json,
        )
        watchdog = SpaPlannerWatchdog(stale_after_seconds=self._settings.spa_planner_watchdog_seconds)
        decision = await watchdog.run(
            control=control,
            runtime=runtime,
            control_service=ArcticSpaControlService(cfg),
            now=now,
            dry_run=dry_run,
        )
        if decision.command_sent:
            event_repo = SpaEnergyEventRepository(session)
            await event_repo.insert(
                consumer_id=consumer.id,
                timestamp=now,
                event_type="watchdog_" + decision.action,
                reason=decision.reason,
                reason_sv=decision.reason_sv,
                strategy=control.strategy,
                dry_run=dry_run,
            )

    async def _actuate(
        self,
        session: AsyncSession,
        *,
        consumer,
        device_config,
        site: SiteModel,
        control,
        plan: LoadPlan,
        now: datetime,
        manual_override: bool,
    ) -> SpaActuatorDecision:
        if is_spa_filter_self_managed(control) and not manual_override:
            return SpaActuatorDecision(
                "plan_only",
                "spa_self_managed",
                "eco_pak_styr_filter",
                dry_run=True,
            )

        cfg = ArcticSpaConfiguration.merge(
            db_enabled=True,
            db_base_url=device_config.api_base_url,
            db_api_key=CredentialCipher().decrypt(device_config.api_key),
            db_spa_id=device_config.external_spa_id,
            db_poll_interval=device_config.poll_interval_seconds,
            db_energy_enabled=device_config.energy_collection_enabled,
            db_cost_enabled=device_config.cost_calculation_enabled,
            db_profiles_json=device_config.power_profiles_json,
        )
        control_service = ArcticSpaControlService(cfg)
        status = self._parse_status(device_config.last_status_json)
        policy = SpaFilterPolicy.from_control(control)
        dry_run = control.dry_run or control.shadow_mode

        actuator_repo = SpaActuatorStateRepository(session)
        runtime = await actuator_repo.get_or_create(consumer.id)

        schedule_result = await ArcticSpaFilterScheduleService().apply_policy(
            control_service,
            policy,
            dry_run=dry_run or not control.filter_optimization_enabled,
            last_known_safe_json=control.last_known_safe_filter_schedule_json,
        )
        if schedule_result.verified:
            control_repo = SpaControlConfigRepository(session)
            await control_repo.update(
                consumer.id,
                last_known_safe_filter_schedule_json=ArcticSpaFilterScheduleService.persist_safe_schedule(
                    policy
                ),
            )
        elif schedule_result.degraded:
            runtime.integration_degraded = True
            runtime.integration_degraded_message_sv = schedule_result.message_sv

        actuator = SpaCleaningActuator(control=control, runtime=runtime, timezone=consumer.timezone)

        decision = await actuator.run_cycle(
            control_service=control_service,
            status=status,
            plan=plan,
            now=now,
            manual_override=manual_override,
        )

        horizon = await self._build_horizon(session, site, consumer.timezone, now)
        surplus_w = horizon[0].available_surplus_w if horizon else 0.0
        price_eur = horizon[0].all_in_price_eur_kwh if horizon else None
        preheat_decision = await actuator.apply_preheat(
            control_service,
            status=status,
            surplus_w=surplus_w,
            price_eur_kwh=price_eur,
            now=now,
        )

        await actuator_repo.save(consumer.id, runtime)
        event_repo = SpaEnergyEventRepository(session)
        await event_repo.insert(
            consumer_id=consumer.id,
            timestamp=now,
            event_type="actuator_" + decision.action,
            reason=decision.reason,
            reason_sv=decision.reason_sv,
            strategy=control.strategy,
            manual_override=manual_override,
            dry_run=decision.dry_run,
            shadow=control.shadow_mode,
        )
        if preheat_decision.command_sent:
            await event_repo.insert(
                consumer_id=consumer.id,
                timestamp=now,
                event_type="preheat_applied",
                reason=preheat_decision.reason,
                reason_sv=preheat_decision.reason_sv,
                strategy=control.strategy,
                dry_run=preheat_decision.dry_run,
            )
        return decision

    async def _build_horizon(
        self,
        session: AsyncSession,
        site: SiteModel,
        timezone: str,
        now: datetime,
    ):
        end = now + timedelta(hours=48)
        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)
        readings_raw = await reading_repo.list_readings(site.id, now - timedelta(days=14), now, limit=5000)
        readings = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings_raw]

        house_provider = HouseLoadForecastProvider()
        house_forecast = house_provider.forecast_series(
            readings,
            timezone=timezone,
            start=now,
            end=end,
        )

        solar_repo = SolarForecastRepository(session)
        solar_forecast = await solar_repo.get_latest(site.id)

        price_repo = MarketPriceRepository(session, is_sqlite=self._settings.is_sqlite)
        prices = await price_repo.list_between(site.id, from_time=now - timedelta(hours=1), to_time=end)
        price_by_hour: dict[datetime, tuple[float | None, float | None]] = {}
        for p in prices:
            hour_key = p.recorded_at.replace(minute=0, second=0, microsecond=0)
            price_by_hour[hour_key] = (p.spot_price_eur_kwh, p.all_in_price_eur_kwh)

        battery_soc = None
        if readings_raw:
            latest = readings_raw[-1]
            battery_soc = latest.battery_soc_pct

        from energy_core.market_prices.currency import sek_to_eur

        fallback_eur = sek_to_eur(site.fallback_purchase_price_sek_kwh, self._settings)
        builder = EnergyHorizonBuilder()
        return builder.build(
            now=now,
            horizon_hours=48,
            inputs=HorizonInputs(
                solar_forecast=solar_forecast,
                house_load=house_forecast,
                price_by_hour=price_by_hour,
                export_value_sek_kwh=site.export_compensation_sek_kwh,
                fallback_price_eur_kwh=fallback_eur,
                initial_battery_soc_pct=battery_soc,
            ),
        )

    def _parse_status(self, raw: str) -> ArcticSpaStatus | None:
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return ArcticSpaStatus.from_api(payload)

    def _source_share(self, window, source: EnergySource) -> float:
        if window.expected_energy_source == source:
            return 1.0
        if window.expected_energy_source == EnergySource.MIXED:
            if source == EnergySource.SOLAR:
                return 0.5
            if source == EnergySource.GRID:
                return 0.5
        return 0.0
