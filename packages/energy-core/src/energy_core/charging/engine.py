"""EMIC smart charging engine — single authority for EV charging."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.framework.factory import ChargerAdapterFactory
from energy_core.chargers.framework.legacy_bridge import LegacyControlBridge
from energy_core.chargers.framework.meter_factory import MeterReaderFactory
from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.charging.anti_flapping import AntiFlappingConfig, AntiFlappingState
from energy_core.charging.command_controller import ChargingCommandController
from energy_core.charging.config import ChargingConfig
from energy_core.charging.display_status import display_status_sv
from energy_core.charging.external_limitation import ExternalLimitationTracker
from energy_core.charging.fuse_diagnostic import fuse_headroom_a_for_charger
from energy_core.charging.models import BridgeStatus, ChargingDecision
from energy_core.charging.optimizer import EvChargingOptimizer
from energy_core.charging.override import override_active
from energy_core.charging.policy import PRICE_MODES, normalized_mode
from energy_core.charging.solar_plan import load_solar_charging_plan_for_charger
from energy_core.charging.signal_filter import EnergySignalFilter
from energy_core.charging.state_machine import (
    SmartChargingRuntime,
    evaluate_smart_charging,
    restore_runtime_from_charger,
)
from energy_core.db.ev_bridge_cycle_repo import EvBridgeCycleRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.energy.heartbeat_provider import HeartbeatEnergyProvider
from energy_core.energy.state import EnergyState
from energy_core.heartbeat_client_factory import create_heartbeat_client

logger = logging.getLogger(__name__)


@dataclass
class ChargerRuntimeState:
    anti_flapping: AntiFlappingState
    optimizer: EvChargingOptimizer
    signal_filter: EnergySignalFilter
    smart_runtime: SmartChargingRuntime
    external_limitation: ExternalLimitationTracker
    last_decision: ChargingDecision | None = None
    last_energy_state: EnergyState | None = None
    last_meter: MeterSnapshot | None = None
    halo_connected: bool | None = None
    vehicle_connected: bool | None = None
    last_error_code: str | None = None
    last_run_at: datetime | None = None
    restored: bool = False


class SmartChargingEngine:
    """Long-lived smart charging control loop authority."""

    def __init__(self) -> None:
        self._runtime: dict[int, ChargerRuntimeState] = {}

    async def run_cycle(self, session: AsyncSession) -> int:
        client = await create_heartbeat_client(session)
        if client is None:
            logger.debug("smart_charging skipped: no HeartBeat client")
            return 0

        chargers = await self._list_active_chargers(session)
        if not chargers:
            return 0

        processed = 0
        now = datetime.now(UTC)
        for charger, site in chargers:
            if not self._is_due(charger, now):
                continue
            try:
                await self._run_charger_cycle(session, client, charger, site, now=now)
                processed += 1
            except Exception:
                logger.exception(
                    "smart_charging charger_id=%s site=%s failed",
                    charger.id,
                    site.slug,
                )
        await session.commit()
        return processed

    async def get_bridge_status(self, charger: EvChargerModel, site: SiteModel | None = None) -> BridgeStatus:
        runtime = self._runtime.get(charger.id)
        if runtime and runtime.last_decision:
            return self._bridge_status_from_runtime(charger, runtime, site=site)
        return bridge_status_from_charger(charger, site=site)

    async def _run_charger_cycle(
        self,
        session: AsyncSession,
        client,
        charger: EvChargerModel,
        site: SiteModel,
        *,
        now: datetime,
    ) -> None:
        if not site.external_system_id:
            logger.warning("smart_charging charger_id=%s missing system_id", charger.id)
            return
        if not charger.external_charger_id and not charger.chargeamp_charger_id:
            logger.warning("smart_charging charger_id=%s missing external charger id", charger.id)
            charger.last_charging_reason = "missing_chargeamp_id"
            charger.last_bridge_run_at = now
            return

        provider = HeartbeatEnergyProvider(
            client,
            system_id=site.external_system_id,
            ev_id=charger.heartbeat_ev_id,
        )
        energy = await provider.get_energy_state(now=now)
        energy = _apply_local_prefs(charger, energy)
        energy = _mark_stale(energy, charger.stale_timeout_seconds)

        config = _charging_config(charger, site)
        adapter = LegacyControlBridge(ChargerAdapterFactory.from_charger_model(charger))
        config = await _clamp_config_to_capabilities(config, adapter)
        runtime = await self._ensure_runtime(session, charger, config)

        is_override = override_active(charger.override_until, now=now)
        if not is_override and charger.override_until is not None and charger.override_until <= now:
            charger.override_until = None

        _, slow_signals = runtime.signal_filter.update(energy)
        mode = charger.charging_mode or "SMART_CHARGE"

        solar_plan = None
        if normalized_mode(mode) not in PRICE_MODES:
            solar_plan = await self._build_solar_plan(session, site, charger, energy, config, now=now)

        optimizer_target = runtime.optimizer.optimize_target(
            energy,
            config=config,
            charging_mode=mode,
            override_active=is_override,
            now=now,
            solar_plan=solar_plan,
        )

        meter = await self._read_meter(charger)
        runtime.last_meter = meter

        halo_connected = runtime.halo_connected
        vehicle_connected = runtime.vehicle_connected
        is_charging = False
        configured_current = meter.configured_current_a if meter else None
        actual_current = meter.actual_charging_current_a if meter else None
        actual_power = meter.power_w if meter else None
        fault_code: str | None = None
        try:
            adapter_status = await adapter.get_status()
            halo_connected = adapter_status.connected
            runtime.halo_connected = adapter_status.connected
            vehicle_connected = adapter_status.vehicle_connected or (meter.vehicle_connected if meter else False)
            runtime.vehicle_connected = vehicle_connected
            is_charging = adapter_status.charging or (meter.is_charging if meter else False)
            if configured_current is None and adapter_status.current_limit_a is not None:
                configured_current = adapter_status.current_limit_a
        except Exception:
            fault_code = "charger_offline"
            if meter is not None:
                vehicle_connected = meter.vehicle_connected
                is_charging = meter.is_charging

        if halo_connected and not vehicle_connected:
            try:
                await adapter.start_charging()
                adapter_status = await adapter.get_status()
                halo_connected = adapter_status.connected
                runtime.halo_connected = adapter_status.connected
                meter = await self._read_meter(charger)
                runtime.last_meter = meter
                vehicle_connected = adapter_status.vehicle_connected or (meter.vehicle_connected if meter else False)
                runtime.vehicle_connected = vehicle_connected
                is_charging = adapter_status.charging or (meter.is_charging if meter else False)
                if configured_current is None and adapter_status.current_limit_a is not None:
                    configured_current = adapter_status.current_limit_a
                if meter is not None:
                    actual_current = meter.actual_charging_current_a
                    actual_power = meter.power_w
                    if meter.configured_current_a is not None:
                        configured_current = meter.configured_current_a
            except Exception:
                logger.debug("charger arm failed charger_id=%s", charger.id, exc_info=True)

        runtime.smart_runtime, decision = evaluate_smart_charging(
            runtime=runtime.smart_runtime,
            config=config,
            charging_mode=mode,
            optimizer_target_a=optimizer_target.target_current_a,
            optimizer_reason=optimizer_target.reason,
            slow_signals=slow_signals,
            vehicle_connected=bool(vehicle_connected),
            halo_connected=bool(halo_connected),
            is_charging=is_charging,
            fault_code=fault_code,
            now=now,
            override_active=is_override,
        )
        decision = replace(
            decision,
            smart_charging_state=runtime.smart_runtime.state.value,
            externally_limited=runtime.smart_runtime.externally_limited,
        )
        runtime.last_decision = decision
        runtime.last_energy_state = energy
        charger.last_heartbeat_data_at = energy.timestamp
        charger.last_bridge_run_at = now
        runtime.last_run_at = now

        applied_a = charger.last_applied_current_a or 0.0
        error_code: str | None = None
        action = decision.action

        try:
            controller = ChargingCommandController(
                adapter,
                anti_flapping=runtime.anti_flapping,
                anti_config=AntiFlappingConfig(
                    min_change_interval_seconds=float(charger.minimum_current_change_interval_seconds),
                    current_hysteresis_a=charger.current_hysteresis_a,
                ),
            )
            result = await controller.apply(decision, now=now)
            status = result.charger_status
            if status is not None:
                runtime.halo_connected = status.connected
                runtime.vehicle_connected = status.vehicle_connected
                vehicle_connected = status.vehicle_connected
                if configured_current is None and status.current_limit_a is not None:
                    configured_current = status.current_limit_a
                if not is_charging:
                    is_charging = status.charging
            error_code = result.error_code
            runtime.last_error_code = error_code
            if result.applied:
                charger.last_applied_current_a = result.applied_current_a
                applied_a = result.applied_current_a
                action = "stop" if result.applied_current_a <= 0 else "set_current"
            else:
                applied_a = result.applied_current_a

            externally_limited = runtime.external_limitation.update(
                requested_current_a=runtime.smart_runtime.requested_current_a,
                configured_current_a=configured_current,
                actual_charging_current_a=actual_current,
                is_charging=is_charging,
                now=now,
            )
            runtime.smart_runtime.externally_limited = externally_limited

            charger.smart_charging_state = runtime.smart_runtime.state.value
            charger.last_requested_current_a = runtime.smart_runtime.requested_current_a
            charger.last_configured_current_a = configured_current
            charger.last_actual_charging_current_a = actual_current
            charger.last_actual_power_w = actual_power
            charger.externally_limited = externally_limited
            charger.last_start_at = runtime.smart_runtime.last_start_at
            charger.last_stop_at = runtime.smart_runtime.last_stop_at

            logger.info(
                "smart_charging state=%s mode=%s export_w=%s import_w=%s requested_a=%.1f applied_a=%.1f "
                "configured_a=%s actual_a=%s external=%s action=%s reason=%s error=%s",
                runtime.smart_runtime.state.value,
                decision.policy_mode,
                slow_signals.grid_export_w,
                slow_signals.grid_import_w,
                runtime.smart_runtime.requested_current_a,
                applied_a,
                configured_current,
                actual_current,
                externally_limited,
                action,
                decision.reason,
                error_code,
            )
        finally:
            charger.last_charging_action = action
            charger.last_charging_reason = decision.reason
            charger.last_charger_error_code = error_code
            charger.last_halo_connected = runtime.halo_connected
            charger.last_vehicle_connected = vehicle_connected
            await self._persist_cycle(
                session,
                charger_id=charger.id,
                recorded_at=now,
                applied_current_a=applied_a,
                price_kwh=energy.electricity_price_eur_kwh,
                policy_mode=decision.policy_mode,
                decision_reason=decision.reason,
                override_active=is_override,
                vehicle_connected=vehicle_connected,
            )

    async def _ensure_runtime(
        self,
        session: AsyncSession,
        charger: EvChargerModel,
        config: ChargingConfig,
    ) -> ChargerRuntimeState:
        runtime = self._runtime.get(charger.id)
        if runtime is None:
            runtime = ChargerRuntimeState(
                anti_flapping=AntiFlappingState(),
                optimizer=EvChargingOptimizer(),
                signal_filter=EnergySignalFilter(),
                smart_runtime=restore_runtime_from_charger(
                    smart_charging_state=charger.smart_charging_state,
                    last_requested_current_a=charger.last_requested_current_a,
                    last_start_at=charger.last_start_at,
                    last_stop_at=charger.last_stop_at,
                ),
                external_limitation=ExternalLimitationTracker(),
            )
            self._runtime[charger.id] = runtime

        if not runtime.restored:
            if runtime.anti_flapping.last_applied_current_a is None and charger.last_applied_current_a is not None:
                runtime.anti_flapping.last_applied_current_a = charger.last_applied_current_a
            if runtime.anti_flapping.last_command_current_a is None and charger.last_requested_current_a is not None:
                runtime.anti_flapping.last_command_current_a = charger.last_requested_current_a
            since = datetime.now(UTC) - timedelta(hours=1)
            cycle_repo = EvBridgeCycleRepository(session)
            runtime.smart_runtime.automatic_starts = await cycle_repo.list_starts_since(
                charger.id,
                since=since,
            )
            runtime.restored = True
        return runtime

    async def _read_meter(self, charger: EvChargerModel) -> MeterSnapshot | None:
        meter = MeterReaderFactory.from_charger_model(charger)
        if meter is None:
            return None
        try:
            return await meter.get_snapshot()
        except Exception:
            logger.debug("meter snapshot failed charger_id=%s", charger.id, exc_info=True)
            return None

    def _bridge_status_from_runtime(
        self,
        charger: EvChargerModel,
        runtime: ChargerRuntimeState,
        *,
        site: SiteModel | None = None,
    ) -> BridgeStatus:
        decision = runtime.last_decision
        energy = runtime.last_energy_state
        meter = runtime.last_meter
        state_value = runtime.smart_runtime.state.value if runtime.smart_runtime else charger.smart_charging_state
        externally_limited = runtime.smart_runtime.externally_limited if runtime.smart_runtime else bool(charger.externally_limited)
        return BridgeStatus(
            charger_id=charger.id,
            bridge_enabled=charger.bridge_enabled,
            charging_mode=charger.charging_mode or "SMART_CHARGE",
            active_policy=decision.policy_mode if decision else (charger.charging_mode or "SMART_CHARGE"),
            ev_target_power_w=energy.ev_target_power_w if energy else None,
            requested_current_a=runtime.smart_runtime.requested_current_a if runtime.smart_runtime else charger.last_requested_current_a,
            applied_current_a=charger.last_applied_current_a,
            previous_current_a=runtime.anti_flapping.last_command_current_a,
            configured_current_a=meter.configured_current_a if meter else charger.last_configured_current_a,
            actual_charging_current_a=meter.actual_charging_current_a if meter else charger.last_actual_charging_current_a,
            actual_power_w=meter.power_w if meter else charger.last_actual_power_w,
            smart_charging_state=state_value,
            externally_limited=externally_limited,
            display_status_sv=display_status_sv(
                state=state_value,
                reason=decision.reason if decision else charger.last_charging_reason,
                externally_limited=externally_limited,
            ),
            fuse_headroom_a=(
                fuse_headroom_a_for_charger(charger, site, energy=energy)
                if site is not None and energy is not None
                else None
            ),
            last_heartbeat_data_at=charger.last_heartbeat_data_at,
            last_bridge_run_at=charger.last_bridge_run_at,
            halo_connected=runtime.halo_connected if runtime.halo_connected is not None else charger.last_halo_connected,
            vehicle_connected=runtime.vehicle_connected if runtime.vehicle_connected is not None else charger.last_vehicle_connected,
            decision_reason=decision.reason if decision else charger.last_charging_reason,
            discovery_hints=energy.raw_field_hints if energy else (),
            stale=bool(energy.stale) if energy else False,
            override_active=override_active(charger.override_until),
            override_until=charger.override_until,
            last_error_code=runtime.last_error_code if runtime.last_error_code else charger.last_charger_error_code,
            last_charging_action=charger.last_charging_action,
            phase_current_l1_a=meter.phase_current_l1_a if meter else (energy.phase_current_l1_a if energy else None),
            phase_current_l2_a=meter.phase_current_l2_a if meter else (energy.phase_current_l2_a if energy else None),
            phase_current_l3_a=meter.phase_current_l3_a if meter else (energy.phase_current_l3_a if energy else None),
        )

    async def _persist_cycle(
        self,
        session: AsyncSession,
        *,
        charger_id: int,
        recorded_at: datetime,
        applied_current_a: float,
        price_kwh: float | None,
        policy_mode: str,
        decision_reason: str,
        override_active: bool,
        vehicle_connected: bool | None,
    ) -> None:
        repo = EvBridgeCycleRepository(session)
        await repo.insert_cycle(
            charger_id=charger_id,
            recorded_at=recorded_at,
            applied_current_a=applied_current_a,
            price_kwh=price_kwh,
            policy_mode=policy_mode,
            decision_reason=decision_reason,
            override_active=override_active,
            vehicle_connected=vehicle_connected,
        )

    async def _build_solar_plan(
        self,
        session: AsyncSession,
        site: SiteModel,
        charger: EvChargerModel,
        energy: EnergyState,
        config: ChargingConfig,
        *,
        now: datetime,
    ):
        return await load_solar_charging_plan_for_charger(
            session,
            site,
            charger,
            now=now,
            price_forecast=energy.price_forecast,
            current_price=energy.electricity_price_eur_kwh,
        )

    async def _list_active_chargers(self, session: AsyncSession) -> list[tuple[EvChargerModel, SiteModel]]:
        result = await session.execute(
            select(EvChargerModel, SiteModel)
            .join(SiteModel, EvChargerModel.site_id == SiteModel.id)
            .where(EvChargerModel.bridge_enabled.is_(True))
        )
        active: list[tuple[EvChargerModel, SiteModel]] = []
        for charger, site in result.all():
            if charger.integration_method or charger.control_source == "chargeamp":
                if charger.external_charger_id or charger.chargeamp_charger_id or charger.integration_method:
                    active.append((charger, site))
        return active

    def _is_due(self, charger: EvChargerModel, now: datetime) -> bool:
        if charger.last_bridge_run_at is None:
            return True
        elapsed = (now - charger.last_bridge_run_at).total_seconds()
        return elapsed >= float(charger.update_interval_seconds)


def bridge_status_from_charger(
    charger: EvChargerModel,
    *,
    site: SiteModel | None = None,
    energy: EnergyState | None = None,
    phase_current_l1_a: float | None = None,
    phase_current_l2_a: float | None = None,
    phase_current_l3_a: float | None = None,
) -> BridgeStatus:
    """Build bridge status from persisted collector state (API path without live runtime)."""
    externally_limited = bool(charger.externally_limited)
    fuse_headroom_a = None
    if site is not None:
        fuse_headroom_a = fuse_headroom_a_for_charger(
            charger,
            site,
            energy=energy,
            phase_current_l1_a=phase_current_l1_a,
            phase_current_l2_a=phase_current_l2_a,
            phase_current_l3_a=phase_current_l3_a,
        )
    return BridgeStatus(
        charger_id=charger.id,
        bridge_enabled=charger.bridge_enabled,
        charging_mode=charger.charging_mode or "SMART_CHARGE",
        active_policy=charger.charging_mode or "SMART_CHARGE",
        ev_target_power_w=None,
        requested_current_a=charger.last_requested_current_a,
        applied_current_a=charger.last_applied_current_a,
        previous_current_a=charger.last_requested_current_a,
        configured_current_a=charger.last_configured_current_a,
        actual_charging_current_a=charger.last_actual_charging_current_a,
        actual_power_w=charger.last_actual_power_w,
        smart_charging_state=charger.smart_charging_state,
        externally_limited=externally_limited,
        display_status_sv=display_status_sv(
            state=charger.smart_charging_state,
            reason=charger.last_charging_reason,
            externally_limited=externally_limited,
        ),
        fuse_headroom_a=fuse_headroom_a,
        last_heartbeat_data_at=charger.last_heartbeat_data_at,
        last_bridge_run_at=charger.last_bridge_run_at,
        halo_connected=charger.last_halo_connected,
        vehicle_connected=charger.last_vehicle_connected,
        decision_reason=charger.last_charging_reason,
        discovery_hints=(),
        stale=False,
        override_active=override_active(charger.override_until),
        override_until=charger.override_until,
        last_error_code=charger.last_charger_error_code,
        last_charging_action=charger.last_charging_action,
        phase_current_l1_a=phase_current_l1_a,
        phase_current_l2_a=phase_current_l2_a,
        phase_current_l3_a=phase_current_l3_a,
    )


def _charging_config(charger: EvChargerModel, site: SiteModel) -> ChargingConfig:
    return ChargingConfig(
        max_current_a=charger.max_current_a,
        min_current_a=charger.min_current_a,
        phases=charger.phases,
        nominal_voltage_v=charger.nominal_voltage_v,
        max_power_w=charger.max_power_w,
        max_grid_import_w=charger.max_grid_import_w,
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a,
        solar_start_threshold_w=charger.solar_start_threshold_w,
        solar_stop_threshold_w=charger.solar_stop_threshold_w,
        solar_start_delay_seconds=float(charger.solar_start_delay_seconds),
        solar_stop_delay_seconds=float(charger.solar_stop_delay_seconds),
        timezone=site.timezone or "Europe/Stockholm",
        deadline_at=charger.deadline_at,
        departure_time=charger.departure_time,
        start_delay_seconds=float(charger.start_delay_seconds),
        stop_delay_seconds=float(charger.stop_delay_seconds),
        minimum_run_time_seconds=float(charger.minimum_run_time_seconds),
        minimum_off_time_seconds=float(charger.minimum_off_time_seconds),
        temporary_grid_import_allowance_w=charger.temporary_grid_import_allowance_w,
        temporary_grid_import_seconds=float(charger.temporary_grid_import_seconds),
        grid_deadband_w=charger.grid_deadband_w,
        minimum_current_change_interval_seconds=float(charger.minimum_current_change_interval_seconds),
        max_current_increase_per_step_a=charger.max_current_increase_per_step_a,
        max_current_decrease_per_step_a=charger.max_current_decrease_per_step_a,
        max_automatic_starts_per_hour=charger.max_automatic_starts_per_hour,
    )


def _apply_local_prefs(charger: EvChargerModel, energy: EnergyState) -> EnergyState:
    mode = charger.charging_mode or energy.heartbeat_charging_mode or "SMART_CHARGE"
    mode_upper = str(mode).upper()
    smart_active = mode_upper in {"SMART_CHARGE", "SMART", "PRICE_CHARGE", "PRICE"}
    target_soc = charger.target_soc_pct / 100.0 if charger.target_soc_pct is not None else energy.target_soc
    return replace(
        energy,
        heartbeat_charging_mode=mode,
        departure_time=charger.departure_time or energy.departure_time,
        deadline_at=charger.deadline_at or energy.deadline_at,
        target_soc=target_soc,
        heartbeat_smart_charge_active=smart_active or energy.heartbeat_smart_charge_active,
    )


def _mark_stale(energy: EnergyState, stale_timeout_seconds: int) -> EnergyState:
    stale = energy.data_age_seconds > stale_timeout_seconds
    return replace(energy, stale=stale)


async def _clamp_config_to_capabilities(config: ChargingConfig, adapter) -> ChargingConfig:
    try:
        capabilities = await adapter.get_capabilities()
    except Exception:
        return config
    return replace(
        config,
        max_current_a=min(config.max_current_a, capabilities.max_current_a),
        min_current_a=max(config.min_current_a, capabilities.min_current_a),
        phases=capabilities.phases if capabilities.phases and capabilities.phases > 0 else config.phases,
    )
