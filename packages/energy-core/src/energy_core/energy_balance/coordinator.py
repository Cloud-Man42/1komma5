"""Collector-side energy balance cycle."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter, MeterSnapshot
from energy_core.config import Settings, get_settings
from energy_core.db.energy_balance_repo import EnergyBalanceRepository, SiteEnergyConfigRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.energy.builder import build_energy_state
from energy_core.energy.state import EnergyState
from energy_core.energy_balance.correlation import correlate_telemetry
from energy_core.energy_balance.engine import EnergyBalanceEngine
from energy_core.sungrow.heartbeat_provider import map_heartbeat_to_sungrow
from energy_core.sungrow.types import SungrowTelemetrySnapshot
from energy_core.virtual_evse.device_profile import VirtualEvseDeviceProfile
from energy_core.virtual_evse.reporter import meter_to_virtual_evse_state
from energy_core.virtual_evse.state import VirtualEvseState
from energy_core.virtual_evse.store import GLOBAL_VIRTUAL_EVSE_STORE

logger = logging.getLogger(__name__)


class EnergyBalanceCoordinator:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._engine = EnergyBalanceEngine(
            residual_warn_w=self._settings.energy_balance_residual_warn_w,
            double_counting_tolerance_w=self._settings.double_counting_tolerance_w,
        )
        self._last_persist: dict[int, datetime] = {}

    async def run_for_charger(
        self,
        session: AsyncSession,
        site: SiteModel,
        charger: EvChargerModel,
        *,
        live_overview: dict | None,
    ) -> None:
        config_repo = SiteEnergyConfigRepository(session)
        site_config = await config_repo.get_or_create(site.id)
        balance_repo = EnergyBalanceRepository(session, is_sqlite=self._settings.is_sqlite)

        sungrow = self._sungrow_from_overview(live_overview)
        halo = await self._halo_snapshot(charger)
        heartbeat = self._heartbeat_state(live_overview, site.timezone)
        virtual_evse = self._virtual_evse_state(
            charger,
            halo,
            heartbeat,
            physical_label=site_config.physical_ev_charger_label,
            ev_label=site_config.ev_vehicle_label,
        )
        if virtual_evse is not None:
            GLOBAL_VIRTUAL_EVSE_STORE.set(charger.id, virtual_evse)

        correlated = correlate_telemetry(
            sungrow=sungrow,
            halo=halo,
            virtual_evse=virtual_evse,
            heartbeat=heartbeat,
            max_alignment_age_seconds=self._settings.max_telemetry_alignment_age_seconds,
        )
        snapshot = self._engine.calculate(
            correlated,
            load_includes_ev_charger=site_config.load_includes_ev_charger,
        )

        if sungrow is not None:
            if sungrow.fresh:
                logger.debug(
                    "Sungrow.Telemetry.Received site=%s age=%.1f",
                    site.slug,
                    sungrow.data_age_seconds,
                )
            else:
                logger.warning(
                    "Sungrow.Telemetry.Stale site=%s age=%.1f", site.slug, sungrow.data_age_seconds
                )

        logger.debug(
            "EnergyBalance.Calculated site=%s charger=%s status=%s",
            site.slug,
            charger.id,
            snapshot.status.value,
        )
        if "residual_high" in snapshot.flags:
            logger.info(
                "EnergyBalance.ResidualHigh site=%s residual=%s", site.slug, snapshot.residual_w
            )
        if "possible_double_counting" in snapshot.flags:
            logger.warning("EnergyBalance.DoubleCountingSuspected site=%s", site.slug)

        if not self._should_persist(charger.id):
            return

        await balance_repo.insert_snapshot(
            site_id=site.id,
            charger_id=charger.id,
            recorded_at=correlated.recorded_at,
            status=snapshot.status.value,
            flags=list(snapshot.flags),
            payload=json.dumps(snapshot.to_dict()),
        )
        self._last_persist[charger.id] = datetime.now(UTC)

    def _should_persist(self, charger_id: int) -> bool:
        last = self._last_persist.get(charger_id)
        if last is None:
            return True
        return (datetime.now(UTC) - last) >= timedelta(seconds=30)

    def _sungrow_from_overview(self, live_overview: dict | None) -> SungrowTelemetrySnapshot | None:
        if not live_overview:
            return None
        return map_heartbeat_to_sungrow(
            live_overview,
            max_age_seconds=self._settings.sungrow_telemetry_max_age_seconds,
        )

    async def _halo_snapshot(self, charger: EvChargerModel) -> MeterSnapshot | None:
        if not charger.chargeamp_charger_id:
            return None
        try:
            adapter = ChargeAmpsMeterAdapter.build(
                charger.chargeamp_charger_id,
                api_key=charger.chargeamps_api_key,
                phases=charger.phases,
                nominal_voltage_v=charger.nominal_voltage_v,
            )
            return await adapter.get_snapshot()
        except Exception:
            logger.debug("Halo meter unavailable for charger %s", charger.id, exc_info=True)
            return None

    def _heartbeat_state(self, live_overview: dict | None, timezone: str) -> EnergyState | None:
        if not live_overview:
            return None
        return build_energy_state(live_overview=live_overview)

    def _virtual_evse_state(
        self,
        charger: EvChargerModel,
        halo: MeterSnapshot | None,
        heartbeat: EnergyState | None,
        *,
        physical_label: str,
        ev_label: str,
    ) -> VirtualEvseState | None:
        if not charger.virtual_evse_enabled or halo is None:
            return None
        profile = VirtualEvseDeviceProfile.for_charger(
            charger.id,
            physical_charger_label=physical_label,
            ev_vehicle_label=ev_label,
            max_power_w=charger.max_power_w or 11000.0,
            name=charger.name,
        )
        return meter_to_virtual_evse_state(
            profile,
            halo,
            stale_timeout_seconds=float(charger.stale_timeout_seconds),
            heartbeat_ev_power_w=heartbeat.ev_actual_power_w if heartbeat else None,
        )
