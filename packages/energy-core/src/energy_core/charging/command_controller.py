"""Apply charging decisions to a physical charger adapter."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.errors import ChargerApiError
from energy_core.chargers.framework.legacy_bridge import LegacyControlBridge
from energy_core.charging.anti_flapping import (
    AntiFlappingConfig,
    AntiFlappingState,
    record_applied,
    should_apply_current,
)
from energy_core.charging.models import ChargingDecision

logger = logging.getLogger(__name__)


@dataclass
class CommandApplyResult:
    applied: bool
    applied_current_a: float
    reason: str
    charger_status: ChargerStatus | None = None
    error_code: str | None = None


class ChargingCommandController:
    """Translate EMIC decisions into deduplicated charger commands."""

    def __init__(
        self,
        adapter: LegacyControlBridge,
        *,
        anti_flapping: AntiFlappingState,
        anti_config: AntiFlappingConfig,
    ) -> None:
        self._adapter = adapter
        self._anti_flapping = anti_flapping
        self._anti_config = anti_config

    async def apply(
        self,
        decision: ChargingDecision,
        *,
        now: datetime | None = None,
    ) -> CommandApplyResult:
        now = now or datetime.now(UTC)
        if decision.action in {"none", "pause"} or decision.skip_apply:
            current = self._anti_flapping.last_command_current_a
            if current is None:
                current = self._anti_flapping.last_applied_current_a or 0.0
            status = await self._safe_get_status()
            return CommandApplyResult(
                applied=False,
                applied_current_a=current,
                reason=decision.reason,
                charger_status=status,
            )

        requested = max(0.0, decision.requested_current_a)
        try:
            status = await self._adapter.get_status()
            if not status.connected:
                current = (
                    self._anti_flapping.last_command_current_a
                    or self._anti_flapping.last_applied_current_a
                    or 0.0
                )
                return CommandApplyResult(
                    applied=False,
                    applied_current_a=current,
                    reason="charger_offline",
                    charger_status=status,
                    error_code="CHARGER_OFFLINE",
                )
            if not status.vehicle_connected and requested > 0:
                current = (
                    self._anti_flapping.last_command_current_a
                    or self._anti_flapping.last_applied_current_a
                    or 0.0
                )
                return CommandApplyResult(
                    applied=False,
                    applied_current_a=current,
                    reason="no_vehicle_connected",
                    charger_status=status,
                )

            actual_limit = status.current_limit_a
            previous_command = self._anti_flapping.last_command_current_a

            if requested <= 0:
                if actual_limit is not None and actual_limit <= 0 and not status.charging:
                    record_applied(self._anti_flapping, 0.0, now=now)
                    return CommandApplyResult(
                        applied=False,
                        applied_current_a=0.0,
                        reason="already_stopped",
                        charger_status=status,
                    )
                if previous_command is not None and previous_command <= 0 and status.charging:
                    await self._adapter.stop_charging()
                    record_applied(self._anti_flapping, 0.0, now=now)
                    return CommandApplyResult(
                        applied=True,
                        applied_current_a=0.0,
                        reason=decision.reason,
                        charger_status=status,
                    )

            if (
                requested > 0
                and previous_command is not None
                and abs(previous_command - requested) < 0.01
            ):
                if status.charging:
                    return CommandApplyResult(
                        applied=False,
                        applied_current_a=previous_command,
                        reason="already_requested",
                        charger_status=status,
                    )

            apply_ok, next_current, anti_reason = should_apply_current(
                requested,
                self._anti_flapping,
                self._anti_config,
                now=now,
            )
            previous_current = self._anti_flapping.last_applied_current_a
            charger_matches_previous = (
                previous_current is not None
                and actual_limit is not None
                and abs(actual_limit - previous_current) < 0.01
                and status.charging == (previous_current > 0)
            )
            if not apply_ok and charger_matches_previous:
                return CommandApplyResult(
                    applied=False,
                    applied_current_a=previous_current,
                    reason=anti_reason,
                    charger_status=status,
                )
            if not apply_ok:
                next_current = requested

            if requested <= 0:
                await self._adapter.stop_charging()
                record_applied(self._anti_flapping, 0.0, now=now)
                return CommandApplyResult(
                    applied=True,
                    applied_current_a=0.0,
                    reason=decision.reason,
                    charger_status=status,
                )

            await self._adapter.set_current(next_current)
            if not status.charging:
                await self._adapter.start_charging()
            record_applied(self._anti_flapping, next_current, now=now)
            return CommandApplyResult(
                applied=True,
                applied_current_a=next_current,
                reason=decision.reason,
                charger_status=status,
            )
        except ChargerApiError as exc:
            current = (
                self._anti_flapping.last_command_current_a
                or self._anti_flapping.last_applied_current_a
                or 0.0
            )
            logger.warning("charging command failed code=%s", exc.code)
            return CommandApplyResult(
                applied=False,
                applied_current_a=current,
                reason=exc.code.lower(),
                error_code=exc.code,
            )

    async def _safe_get_status(self) -> ChargerStatus | None:
        try:
            return await self._adapter.get_status()
        except ChargerApiError as exc:
            logger.debug("charger status refresh failed code=%s", exc.code)
            return None
