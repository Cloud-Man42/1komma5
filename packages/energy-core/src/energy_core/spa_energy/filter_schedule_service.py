"""Transactional Arctic Spa filter schedule read/write with verification."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from energy_core.integrations.arctic_spa.client import ArcticSpaApiError
from energy_core.integrations.arctic_spa.control_service import ArcticSpaControlService
from energy_core.spa_energy.filter_policy import SpaFilterPolicy

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FilterScheduleSnapshot:
    frequency: int
    duration_hours: int

    def matches_policy(self, policy: SpaFilterPolicy) -> bool:
        return (
            self.frequency == policy.cycles_per_day
            and self.duration_hours == max(1, policy.duration_per_cycle_minutes // 60)
        )


@dataclass(frozen=True, slots=True)
class FilterScheduleUpdateResult:
    success: bool
    verified: bool
    previous: FilterScheduleSnapshot | None
    applied: FilterScheduleSnapshot | None
    message_sv: str
    degraded: bool = False
    restored_baseline: bool = False


class ArcticSpaFilterScheduleService:
    """Ensure spa internal schedule stays at 4×2 h; never write zero values."""

    async def read_snapshot(self, control_service: ArcticSpaControlService) -> FilterScheduleSnapshot:
        status = await control_service.get_status()
        frequency = max(1, int(round(float(status.filter_frequency or 1))))
        duration = max(1, int(round(float(status.filter_duration or 2))))
        return FilterScheduleSnapshot(frequency=frequency, duration_hours=duration)

    async def apply_policy(
        self,
        control_service: ArcticSpaControlService,
        policy: SpaFilterPolicy,
        *,
        dry_run: bool,
        last_known_safe_json: str | None,
    ) -> FilterScheduleUpdateResult:
        target = FilterScheduleSnapshot(
            frequency=max(1, policy.cycles_per_day),
            duration_hours=max(1, policy.duration_per_cycle_minutes // 60),
        )
        if target.frequency < 1 or target.duration_hours < 1:
            return FilterScheduleUpdateResult(
                success=False,
                verified=False,
                previous=None,
                applied=None,
                message_sv="Ogiltigt filterschema — frekvens och varaktighet måste vara minst 1.",
                degraded=True,
            )

        try:
            previous = await self.read_snapshot(control_service)
        except ArcticSpaApiError as exc:
            return FilterScheduleUpdateResult(
                success=False,
                verified=False,
                previous=None,
                applied=None,
                message_sv=f"Kunde inte läsa spa-filterschema: {exc}",
                degraded=True,
            )

        if previous.matches_policy(policy):
            return FilterScheduleUpdateResult(
                success=True,
                verified=True,
                previous=previous,
                applied=previous,
                message_sv="Spa-filterschema matchar redan EMIC-kravet.",
            )

        if dry_run:
            return FilterScheduleUpdateResult(
                success=True,
                verified=False,
                previous=previous,
                applied=target,
                message_sv="Torrt läge — filterschema skulle uppdateras till 4×2 h.",
            )

        try:
            await control_service.ensure_safety_floor(
                frequency_per_day=float(target.frequency),
                duration_hours=float(target.duration_hours),
            )
            applied = await self.read_snapshot(control_service)
            verified = applied.matches_policy(policy)
            if verified:
                return FilterScheduleUpdateResult(
                    success=True,
                    verified=True,
                    previous=previous,
                    applied=applied,
                    message_sv="Filterschema verifierat mot Arctic Spa.",
                )

            restored = await self._restore_baseline(
                control_service,
                last_known_safe_json,
                fallback=target,
            )
            return FilterScheduleUpdateResult(
                success=False,
                verified=False,
                previous=previous,
                applied=applied,
                message_sv=(
                    "Filterschema skrevs men read-back matchade inte. "
                    + ("Säker baslinje återställd." if restored else "Kunde inte återställa baslinje.")
                ),
                degraded=True,
                restored_baseline=restored,
            )
        except ArcticSpaApiError as exc:
            restored = await self._restore_baseline(
                control_service,
                last_known_safe_json,
                fallback=target,
            )
            return FilterScheduleUpdateResult(
                success=False,
                verified=False,
                previous=previous,
                applied=None,
                message_sv=f"Filterschema kunde inte skrivas: {exc}. "
                + ("Säker baslinje återställd." if restored else ""),
                degraded=True,
                restored_baseline=restored,
            )

    async def restore_safe_baseline(
        self,
        control_service: ArcticSpaControlService,
        last_known_safe_json: str | None,
        *,
        policy: SpaFilterPolicy,
        dry_run: bool,
    ) -> FilterScheduleUpdateResult:
        fallback = FilterScheduleSnapshot(
            frequency=max(1, policy.cycles_per_day),
            duration_hours=max(1, policy.duration_per_cycle_minutes // 60),
        )
        if dry_run:
            return FilterScheduleUpdateResult(
                success=True,
                verified=False,
                previous=None,
                applied=fallback,
                message_sv="Torrt läge — skulle återställa säker filter-baslinje.",
            )
        restored = await self._restore_baseline(control_service, last_known_safe_json, fallback=fallback)
        try:
            applied = await self.read_snapshot(control_service)
        except ArcticSpaApiError:
            applied = None
        return FilterScheduleUpdateResult(
            success=restored,
            verified=applied.matches_policy(policy) if applied else False,
            previous=None,
            applied=applied,
            message_sv="Säker filter-baslinje återställd." if restored else "Kunde inte återställa filter-baslinje.",
            degraded=not restored,
            restored_baseline=restored,
        )

    async def _restore_baseline(
        self,
        control_service: ArcticSpaControlService,
        last_known_safe_json: str | None,
        *,
        fallback: FilterScheduleSnapshot,
    ) -> bool:
        safe = SpaFilterPolicy.safe_schedule_from_json(last_known_safe_json)
        freq = safe["frequency"] if safe else fallback.frequency
        dur = safe["duration_hours"] if safe else fallback.duration_hours
        freq = max(1, int(freq))
        dur = max(1, int(dur))
        try:
            await control_service.ensure_safety_floor(
                frequency_per_day=float(freq),
                duration_hours=float(dur),
            )
            logger.warning("Restored spa filter baseline frequency=%s duration=%s", freq, dur)
            return True
        except ArcticSpaApiError:
            return False

    @staticmethod
    def persist_safe_schedule(policy: SpaFilterPolicy) -> str:
        return policy.to_safe_schedule_json()
