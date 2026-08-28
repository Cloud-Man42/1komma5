"""Planner watchdog — recover spa safety floor when EMIC stops planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from energy_core.db.spa_control_repo import SpaControlConfigRecord
from energy_core.integrations.arctic_spa.client import ArcticSpaApiError
from energy_core.integrations.arctic_spa.control_service import ArcticSpaControlService
from energy_core.spa_energy.filter_policy import is_spa_filter_self_managed
from energy_core.spa_energy.runtime import DEGRADED_MESSAGE_SV, SpaActuatorRuntime, SpaActuatorState


@dataclass(frozen=True, slots=True)
class WatchdogDecision:
    action: str
    reason: str
    reason_sv: str
    command_sent: bool = False
    dry_run: bool = False


class SpaPlannerWatchdog:
    """Ensure the spa internal schedule stays at the safety floor if planning stalls."""

    def __init__(self, *, stale_after_seconds: int = 180) -> None:
        self._stale_after = timedelta(seconds=stale_after_seconds)

    async def run(
        self,
        *,
        control: SpaControlConfigRecord,
        runtime: SpaActuatorRuntime,
        control_service: ArcticSpaControlService,
        now: datetime,
        dry_run: bool,
    ) -> WatchdogDecision:
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if not control.smart_control_enabled or dry_run or is_spa_filter_self_managed(control):
            return WatchdogDecision("none", "watchdog_inactive", "vakt_inaktiv")
        if runtime.last_planner_run_at is None:
            return WatchdogDecision("none", "watchdog_no_baseline", "vakt_ingen_baslinje")

        stale = now - runtime.last_planner_run_at > self._stale_after
        if not stale:
            return WatchdogDecision("none", "watchdog_ok", "vakt_ok")

        if runtime.state not in {SpaActuatorState.WAITING, SpaActuatorState.IDLE, SpaActuatorState.COOLDOWN}:
            return WatchdogDecision("none", "watchdog_active_cleaning", "vakt_cleaning_pagar")

        try:
            await control_service.ensure_safety_floor(
                frequency_per_day=control.safety_floor_frequency_per_day,
                duration_hours=control.safety_floor_duration_hours,
            )
            runtime.integration_degraded = True
            runtime.integration_degraded_message_sv = (
                "EMIC-planering har varit otillgänglig. Spaet har återställts till sitt säkerhetsgolv."
            )
            runtime.filter_held_off_until = None
            runtime.state = SpaActuatorState.DEGRADED
            return WatchdogDecision(
                "recover",
                "watchdog_safety_floor_restored",
                "vakt_sakerhetsgolv",
                command_sent=True,
            )
        except ArcticSpaApiError:
            runtime.integration_degraded = True
            runtime.integration_degraded_message_sv = DEGRADED_MESSAGE_SV
            runtime.state = SpaActuatorState.DEGRADED
            return WatchdogDecision("none", "watchdog_api_failed", "vakt_api_fel")
