"""Bidirectional sync between EMIC charger prefs and Heartbeat EV profiles."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.heartbeat.ev_control import HeartbeatEvSettings, parse_ev_settings, settings_differ
from energy_core.heartbeat_client import HeartbeatClient
from energy_core.heartbeat_client_factory import create_heartbeat_client

logger = logging.getLogger(__name__)

PUSH_COOLDOWN_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class HeartbeatSyncResult:
    pulled: bool = False
    pushed: bool = False
    applied_remote: bool = False
    skipped: bool = False
    error: str | None = None


class HeartbeatEvSyncService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._charger_repo = EvChargerRepository(session)
        self._settings_repo = HeartbeatSettingsRepository(session)

    async def sync_charger(
        self,
        charger: EvChargerModel,
        site: SiteModel,
        *,
        client: HeartbeatClient | None = None,
        force_push: bool = False,
    ) -> HeartbeatSyncResult:
        if not await self._settings_repo.is_write_enabled():
            return HeartbeatSyncResult(skipped=True)
        if not charger.heartbeat_sync_enabled or not charger.heartbeat_ev_id:
            return HeartbeatSyncResult(skipped=True)
        if not site.external_system_id:
            return HeartbeatSyncResult(skipped=True, error="missing_system_id")

        owns_client = client is None
        if client is None:
            client = await create_heartbeat_client(self._session)
        if client is None:
            return HeartbeatSyncResult(skipped=True, error="heartbeat_not_configured")

        now = datetime.now(UTC)
        try:
            remote_ev = await client.fetch_ev_by_id(site.external_system_id, charger.heartbeat_ev_id)
            remote = parse_ev_settings(remote_ev)
            local = _local_settings(charger)

            if _remote_wins(charger, remote, now=now):
                applied = await self._apply_remote(charger, remote)
                await self._charger_repo.update(
                    charger,
                    heartbeat_last_pulled_at=now,
                    heartbeat_remote_updated_at=remote.remote_updated_at,
                    clear_heartbeat_sync_error=True,
                )
                return HeartbeatSyncResult(pulled=True, applied_remote=applied)

            if force_push or settings_differ(local, remote):
                await self._push_settings(
                    client,
                    site.external_system_id,
                    charger,
                    local=local,
                    now=now,
                )
                return HeartbeatSyncResult(pushed=True)

            await self._charger_repo.update(
                charger,
                heartbeat_last_pulled_at=now,
                heartbeat_remote_updated_at=remote.remote_updated_at or charger.heartbeat_remote_updated_at,
                clear_heartbeat_sync_error=True,
            )
            return HeartbeatSyncResult(pulled=True)
        except Exception as exc:
            message = str(exc)[:512]
            logger.warning(
                "heartbeat sync failed charger_id=%s site=%s: %s",
                charger.id,
                site.slug,
                message,
            )
            await self._charger_repo.update(charger, heartbeat_sync_error=message)
            return HeartbeatSyncResult(error=message)
        finally:
            if owns_client:
                pass

    async def push_charger(
        self,
        charger: EvChargerModel,
        site: SiteModel,
        *,
        client: HeartbeatClient | None = None,
        target_soc_pct: float | None = None,
    ) -> HeartbeatSyncResult:
        if not await self._settings_repo.is_write_enabled():
            return HeartbeatSyncResult(skipped=True)
        if not charger.heartbeat_sync_enabled or not charger.heartbeat_ev_id or not site.external_system_id:
            return HeartbeatSyncResult(skipped=True)

        owns_client = client is None
        if client is None:
            client = await create_heartbeat_client(self._session)
        if client is None:
            return HeartbeatSyncResult(skipped=True, error="heartbeat_not_configured")

        now = datetime.now(UTC)
        local = _local_settings(charger)
        if target_soc_pct is not None:
            local = HeartbeatEvSettings(
                charging_mode=local.charging_mode,
                target_soc_pct=target_soc_pct,
                departure_time=local.departure_time,
                remote_updated_at=local.remote_updated_at,
            )
        try:
            await self._push_settings(
                client,
                site.external_system_id,
                charger,
                local=local,
                now=now,
            )
            return HeartbeatSyncResult(pushed=True)
        except Exception as exc:
            message = str(exc)[:512]
            await self._charger_repo.update(charger, heartbeat_sync_error=message)
            return HeartbeatSyncResult(error=message)

    async def _push_settings(
        self,
        client: HeartbeatClient,
        system_id: str,
        charger: EvChargerModel,
        *,
        local: HeartbeatEvSettings,
        now: datetime,
    ) -> None:
        await client.update_ev_charge_settings(
            system_id,
            charger.heartbeat_ev_id or "",
            charging_mode=local.charging_mode,
            target_soc_pct=local.target_soc_pct,
            departure_time=local.departure_time,
        )
        await self._charger_repo.update(
            charger,
            heartbeat_last_pushed_at=now,
            clear_heartbeat_sync_error=True,
        )

    async def _apply_remote(self, charger: EvChargerModel, remote: HeartbeatEvSettings) -> bool:
        updates: dict[str, object] = {}
        if remote.charging_mode and remote.charging_mode != (charger.charging_mode or "").upper():
            updates["charging_mode"] = remote.charging_mode
        if remote.target_soc_pct is not None and remote.target_soc_pct != charger.target_soc_pct:
            updates["target_soc_pct"] = remote.target_soc_pct
        if remote.departure_time is not None and remote.departure_time != charger.departure_time:
            updates["departure_time"] = remote.departure_time
        if not updates:
            return False
        await self._charger_repo.update(charger, **updates)
        return True


def _local_settings(charger: EvChargerModel) -> HeartbeatEvSettings:
    return HeartbeatEvSettings(
        charging_mode=charger.charging_mode,
        target_soc_pct=charger.target_soc_pct,
        departure_time=charger.departure_time,
        remote_updated_at=charger.heartbeat_remote_updated_at,
    )


def _remote_wins(charger: EvChargerModel, remote: HeartbeatEvSettings, *, now: datetime) -> bool:
    if remote.remote_updated_at is None:
        return False
    last_push = charger.heartbeat_last_pushed_at
    if last_push is not None and remote.remote_updated_at <= last_push + timedelta(seconds=PUSH_COOLDOWN_SECONDS):
        return False
    if charger.heartbeat_remote_updated_at is not None and remote.remote_updated_at <= charger.heartbeat_remote_updated_at:
        return False
    local = _local_settings(charger)
    if not settings_differ(local, remote):
        return False
    if last_push is None:
        return True
    return remote.remote_updated_at > last_push
