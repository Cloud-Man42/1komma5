"""Spa cleaning actuator state machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from energy_core.db.spa_control_repo import SpaControlConfigRecord
from energy_core.flexible_load.types import LoadPlan, PlanWindow
from energy_core.integrations.arctic_spa.client import ArcticSpaApiError
from energy_core.integrations.arctic_spa.control_service import ArcticSpaControlService
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus


from energy_core.spa_energy.filter_policy import is_spa_filter_self_managed
from energy_core.spa_energy.runtime import (
    DEGRADED_MESSAGE_SV,
    SpaActuatorRuntime,
    SpaActuatorState,
)


@dataclass(frozen=True, slots=True)
class SpaActuatorDecision:
    action: str
    reason: str
    reason_sv: str
    command_sent: bool = False
    dry_run: bool = False


def _today_key(now: datetime, timezone: str) -> str:
    from zoneinfo import ZoneInfo

    return now.astimezone(ZoneInfo(timezone)).strftime("%Y-%m-%d")


class SpaCleaningActuator:
    """Execute planned cleaning windows with anti-flapping and safety rules."""

    def __init__(
        self,
        *,
        control: SpaControlConfigRecord,
        runtime: SpaActuatorRuntime,
        timezone: str,
    ) -> None:
        self._control = control
        self._runtime = runtime
        self._timezone = timezone

    async def run_cycle(
        self,
        *,
        control_service: ArcticSpaControlService,
        status: ArcticSpaStatus | None,
        plan: LoadPlan | None,
        now: datetime,
        manual_override: bool = False,
    ) -> SpaActuatorDecision:
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        day_key = _today_key(now, self._timezone)
        if self._runtime.starts_day != day_key:
            self._runtime.starts_day = day_key
            self._runtime.starts_today = 0

        if status and status.errors:
            self._runtime.integration_degraded = True
            self._runtime.integration_degraded_message_sv = DEGRADED_MESSAGE_SV
            self._runtime.state = SpaActuatorState.DEGRADED
            return SpaActuatorDecision("none", "spa_fault", "spa_fel", dry_run=self._control.dry_run)

        auto_dry_run = self._control.dry_run or self._control.shadow_mode
        if auto_dry_run and not manual_override:
            return SpaActuatorDecision("plan_only", "dry_run", "torrkorning", dry_run=True)

        if is_spa_filter_self_managed(self._control) and not manual_override:
            return SpaActuatorDecision("plan_only", "spa_self_managed", "eco_pak_styr_filter", dry_run=True)

        if manual_override:
            # Explicit user action — honor dry_run test flag but not shadow mode.
            manual_dry_run = self._control.dry_run
            return await self._start_cleaning(
                control_service,
                now=now,
                reason="manual_override",
                reason_sv="manuell_overstyrning",
                dry_run=manual_dry_run,
            )

        if self._runtime.integration_degraded:
            return SpaActuatorDecision("none", "integration_degraded", "integration_degraderad", dry_run=auto_dry_run)

        window = self._select_window(plan, now)

        if self._runtime.state == SpaActuatorState.CLEANING:
            return await self._handle_active_cleaning(control_service, status, now, auto_dry_run, window)

        if window is None:
            return SpaActuatorDecision("none", "no_plan", "ingen_plan", dry_run=auto_dry_run)

        if now < window.start:
            if now >= window.start - timedelta(minutes=5):
                return SpaActuatorDecision("wait", "pre_window", "vantar_fonster", dry_run=auto_dry_run)
            return SpaActuatorDecision("none", "scheduled", "planerad", dry_run=auto_dry_run)

        if window.start <= now < window.end:
            if self._cooldown_blocks_start(now):
                return SpaActuatorDecision("none", "cooldown", "paus", dry_run=auto_dry_run)
            return await self._start_cleaning(
                control_service,
                now=now,
                reason=plan.reason if plan else "scheduled",
                reason_sv=plan.reason_sv if plan else "planerad",
                dry_run=auto_dry_run,
                stop_at=window.end,
            )

        return SpaActuatorDecision("none", "window_passed", "fonster_passerat", dry_run=auto_dry_run)

    def _select_window(self, plan: LoadPlan | None, now: datetime) -> PlanWindow | None:
        if not plan or not plan.windows:
            return None
        for window in plan.windows:
            if window.start <= now < window.end:
                return window
        upcoming = [w for w in plan.windows if w.start > now]
        if upcoming:
            return min(upcoming, key=lambda w: w.start)
        return plan.windows[-1]

    async def apply_preheat(
        self,
        control_service: ArcticSpaControlService,
        *,
        status: ArcticSpaStatus | None,
        surplus_w: float,
        price_eur_kwh: float | None,
        now: datetime,
    ) -> SpaActuatorDecision:
        if not self._control.smart_preheat_enabled:
            return SpaActuatorDecision("none", "preheat_disabled", "forvarmning_av", dry_run=self._control.dry_run)
        if self._control.dry_run or self._control.shadow_mode:
            return SpaActuatorDecision("none", "preheat_dry_run", "forvarmning_tor", dry_run=True)
        if status is None or not status.connected:
            return SpaActuatorDecision("none", "preheat_offline", "forvarmning_offline", dry_run=False)

        target_c = min(self._control.max_preheat_temperature_c, self._control.normal_temperature_c + 1.0)
        target_c = max(target_c, self._control.min_comfort_temperature_c)
        cheap = price_eur_kwh is not None and price_eur_kwh <= 0.15
        enough_surplus = surplus_w >= 1500
        if not enough_surplus and not cheap:
            return SpaActuatorDecision("none", "preheat_skip", "forvarmning_skip", dry_run=False)
        if status.setpoint_c is not None and status.setpoint_c >= target_c - 0.1:
            return SpaActuatorDecision("none", "preheat_ok", "forvarmning_redan", dry_run=False)

        try:
            await control_service.set_target_temperature_c(target_c)
            self._runtime.last_command_at = now
            return SpaActuatorDecision(
                "preheat",
                "preheat_applied",
                "forvarmning_aktiv",
                command_sent=True,
                dry_run=False,
            )
        except ArcticSpaApiError:
            self._runtime.integration_degraded = True
            self._runtime.integration_degraded_message_sv = DEGRADED_MESSAGE_SV
            return SpaActuatorDecision("none", "preheat_failed", "forvarmning_fel", dry_run=False)

    def _cooldown_blocks_start(self, now: datetime) -> bool:
        if self._runtime.last_stop_at is None:
            return False
        min_stop = timedelta(minutes=self._control.minimum_cycle_separation_minutes)
        return now - self._runtime.last_stop_at < min_stop

    async def _start_cleaning(
        self,
        control_service: ArcticSpaControlService,
        *,
        now: datetime,
        reason: str,
        reason_sv: str,
        dry_run: bool,
        stop_at: datetime | None = None,
    ) -> SpaActuatorDecision:
        if self._runtime.starts_today >= self._control.filter_cycles_per_day:
            return SpaActuatorDecision("none", "max_starts", "max_starter", dry_run=dry_run)

        min_run = timedelta(minutes=self._control.filter_duration_minutes)
        if dry_run:
            self._runtime.state = SpaActuatorState.WAITING
            self._runtime.last_reason = reason
            self._runtime.last_reason_sv = reason_sv
            return SpaActuatorDecision("start", reason, reason_sv, dry_run=True)

        try:
            await control_service.ensure_safety_floor(
                frequency_per_day=self._control.safety_floor_frequency_per_day,
                duration_hours=self._control.safety_floor_duration_hours,
            )
            await control_service.start_filtering()
            self._runtime.state = SpaActuatorState.CLEANING
            self._runtime.cleaning_started_at = now
            self._runtime.cleaning_stop_at = stop_at or (now + min_run)
            self._runtime.last_command_at = now
            self._runtime.starts_today += 1
            self._runtime.last_reason = reason
            self._runtime.last_reason_sv = reason_sv
            return SpaActuatorDecision("start", reason, reason_sv, command_sent=True, dry_run=False)
        except ArcticSpaApiError:
            self._runtime.integration_degraded = True
            self._runtime.integration_degraded_message_sv = DEGRADED_MESSAGE_SV
            self._runtime.state = SpaActuatorState.DEGRADED
            return SpaActuatorDecision("none", "api_failed", "api_fel", dry_run=False)

    async def _handle_active_cleaning(
        self,
        control_service: ArcticSpaControlService,
        status: ArcticSpaStatus | None,
        now: datetime,
        dry_run: bool,
        window: PlanWindow | None = None,
    ) -> SpaActuatorDecision:
        started = self._runtime.cleaning_started_at
        stop_at = self._runtime.cleaning_stop_at
        min_run = timedelta(minutes=self._control.filter_duration_minutes)

        if started and now - started < min_run:
            return SpaActuatorDecision("hold", "min_run", "min_kortid", dry_run=dry_run)

        # Anti-flapping: hold through planned window end even if solar dips briefly
        if window and now < window.end:
            return SpaActuatorDecision("hold", "cleaning_active", "cleaning_pagar", dry_run=dry_run)

        if stop_at and now >= stop_at:
            if dry_run:
                self._runtime.state = SpaActuatorState.COOLDOWN
                self._runtime.last_stop_at = now
                return SpaActuatorDecision("stop", "window_end", "fonster_slut", dry_run=True)
            try:
                await control_service.stop_filtering()
                self._runtime.state = SpaActuatorState.COOLDOWN
                self._runtime.last_stop_at = now
                self._runtime.cleaning_started_at = None
                self._runtime.cleaning_stop_at = None
                return SpaActuatorDecision("stop", "window_end", "fonster_slut", command_sent=True, dry_run=False)
            except ArcticSpaApiError:
                self._runtime.integration_degraded = True
                self._runtime.integration_degraded_message_sv = DEGRADED_MESSAGE_SV
                return SpaActuatorDecision("hold", "stop_failed", "stopp_fel", dry_run=False)

        if status and status.filter_status in {"Idle", "Suspended"} and started and now - started >= min_run:
            self._runtime.state = SpaActuatorState.IDLE
            self._runtime.last_stop_at = now
            return SpaActuatorDecision("done", "cleaning_complete", "cleaning_klar", dry_run=dry_run)

        return SpaActuatorDecision("hold", "cleaning_active", "cleaning_pagar", dry_run=dry_run)
