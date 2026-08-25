"""Safe Heartbeat EV write test — admin triggered only."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat.discovery.models import WriteTestResult
from energy_core.heartbeat.write_test.client import HeartbeatWriteClient
from energy_core.heartbeat_client_factory import create_heartbeat_client


class HeartbeatWriteTestService:
    EV_CHARGE_TYPES = frozenset({"EV_CHARGE_FROM_GRID", "EV_CHARGE", "CHARGE_EV"})

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = HeartbeatDiscoveryRepository(session)
        self._charger_repo = EvChargerRepository(session)

    async def run(
        self,
        site_slug: str,
        *,
        dry_run: bool = True,
        heartbeat_ev_id: str | None = None,
    ) -> WriteTestResult:
        site = await self._charger_repo.get_site_by_slug(site_slug)
        if site is None:
            raise ValueError("Site not found")
        if not site.external_system_id:
            raise ValueError("Site has no Heartbeat system ID")

        settings = await self._repo.get_or_create_bridge_settings(site.id)
        if not settings.write_enabled and not dry_run:
            raise ValueError("Write test is disabled. Enable write_enabled in bridge settings first.")

        mappings = await self._repo.list_mappings(site.id)
        ev_id = heartbeat_ev_id or (mappings[0].heartbeat_ev_id if mappings else None)
        if not ev_id:
            raise ValueError("No Heartbeat EV ID available. Run discovery first.")

        if mappings and mappings[0].confidence_pct < settings.confidence_threshold_pct:
            raise ValueError(
                f"EV confidence {mappings[0].confidence_pct}% below threshold "
                f"{settings.confidence_threshold_pct}%"
            )

        client = await create_heartbeat_client(self._session)
        if client is None:
            raise ValueError("Heartbeat client not available")

        steps: list[dict[str, Any]] = []
        started = datetime.now(UTC)

        ev = await client.fetch_ev_by_id(site.external_system_id, ev_id)
        if not ev:
            result = WriteTestResult(classification="WRITE_UNSUPPORTED", error="EV not found on read-back GET")
            await self._persist(site.id, ev_id, dry_run, steps, result, started)
            return result

        steps.append({"step": "read_ev", "status": "PASS", "ev_id": ev_id})

        manual_soc = ev.get("manualSoc")
        charge_settings = ev.get("chargeSettings") or {}
        target_soc = charge_settings.get("targetSoc")

        payload: dict[str, Any] = {}
        field = "manualSoc"
        current_value = manual_soc
        if manual_soc is not None:
            payload["manualSoc"] = manual_soc
        elif target_soc is not None:
            payload["chargeSettings"] = {"targetSoc": target_soc}
            field = "targetSoc"
            current_value = target_soc
        else:
            result = WriteTestResult(classification="WRITE_UNSUPPORTED", error="No idempotent SoC field to test")
            await self._persist(site.id, ev_id, dry_run, steps, result, started)
            return result

        steps.append(
            {
                "step": "dry_run_preview",
                "method": "PATCH",
                "path": f"/v1/systems/{site.external_system_id}/devices/evs/{ev_id}",
                "payload": payload,
                "current_value": current_value,
                "proposed_value": current_value,
            }
        )

        if dry_run:
            result = WriteTestResult(
                classification="DRY_RUN",
                requested_value=current_value,
                steps=steps,
            )
            await self._persist(site.id, ev_id, True, steps, result.__dict__, started)
            await self._session.commit()
            return result

        write_client = HeartbeatWriteClient(client)
        t0 = time.perf_counter()
        status, body = await write_client.patch_ev(site.external_system_id, ev_id, payload)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        steps.append({"step": "patch", "http_status": status, "response": body, "duration_ms": duration_ms})

        if status in {401, 403}:
            classification = "AUTHORIZATION_FAILED"
        elif status == 404:
            classification = "WRITE_UNSUPPORTED"
        elif status >= 400:
            classification = "WRITE_REJECTED"
        else:
            classification = "WRITE_ACCEPTED_AND_CONFIRMED"

        read_back = await client.fetch_ev_by_id(site.external_system_id, ev_id)
        read_value = None
        if read_back:
            read_value = read_back.get("manualSoc") if field == "manualSoc" else (read_back.get("chargeSettings") or {}).get("targetSoc")

        if classification == "WRITE_ACCEPTED_AND_CONFIRMED" and read_value != current_value:
            classification = "WRITE_ACCEPTED_NOT_VISIBLE"

        result = WriteTestResult(
            classification=classification,
            requested_value=current_value,
            http_status=status,
            read_back_value=read_value,
            duration_ms=duration_ms,
            steps=steps,
        )
        await self._persist(site.id, ev_id, False, steps, result.__dict__, started)
        await self._session.commit()
        return result

    async def _persist(
        self,
        site_id: int,
        ev_id: str,
        dry_run: bool,
        steps: list[dict[str, Any]],
        result: Any,
        started: datetime,
    ) -> None:
        data = result if isinstance(result, dict) else result.__dict__
        await self._repo.save_write_test(
            site_id,
            ev_id,
            str(data.get("classification", "UNKNOWN")),
            dry_run=dry_run,
            steps=steps,
            result=data,
            started_at=started,
            completed_at=datetime.now(UTC),
        )
