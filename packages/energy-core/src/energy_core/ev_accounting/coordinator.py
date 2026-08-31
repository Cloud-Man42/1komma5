"""Orchestrate EV energy accounting in the collector loop."""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import SiteModel
from energy_core.db.repositories import MarketPriceRepository
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.ev_accounting.sampler import EVSessionSampler
from energy_core.ev_accounting.session_service import EVSessionService
from energy_core.heartbeat.live_overview import parse_live_overview
from energy_core.secrets import CredentialCipher

logger = logging.getLogger(__name__)

_CORE_OVERVIEW_FIELDS = (
    "pv_power_w",
    "home_consumption_w",
    "grid_import_w",
    "grid_export_w",
    "battery_charge_power_w",
    "battery_discharge_power_w",
)


def _overview_has_measurements(parsed: dict[str, Any]) -> bool:
    return any(parsed.get(field) is not None for field in _CORE_OVERVIEW_FIELDS)


def _sample_from_parsed(
    parsed: dict[str, Any],
    *,
    price_sek_kwh: float,
    duration_hours: float,
) -> SiteEnergySample | None:
    if not _overview_has_measurements(parsed):
        return None
    return SiteEnergySample(
        pv_power_w=float(parsed.get("pv_power_w") or 0.0),
        house_consumption_w=float(parsed.get("home_consumption_w") or 0.0),
        grid_import_w=float(parsed.get("grid_import_w") or 0.0),
        grid_export_w=float(parsed.get("grid_export_w") or 0.0),
        battery_charge_w=float(parsed.get("battery_charge_power_w") or 0.0),
        battery_discharge_w=float(parsed.get("battery_discharge_power_w") or 0.0),
        ev_power_w=float(parsed.get("ev_actual_power_w") or 0.0),
        electricity_price_sek_kwh=price_sek_kwh,
        duration_hours=duration_hours,
    )


class EVAccountingCoordinator:
    """Run session lifecycle, interval sampling, and battery ledger updates."""

    def __init__(self) -> None:
        self._session_service = EVSessionService()
        self._sampler = EVSessionSampler(self._session_service)

    @property
    def session_service(self) -> EVSessionService:
        return self._session_service

    async def setup(self, session: AsyncSession) -> None:
        await self._session_service.resume_active_sessions(session)

    async def process_site(
        self,
        db: AsyncSession,
        *,
        site: SiteModel,
        live_overview: dict | None,
        is_sqlite: bool,
    ) -> int:
        processed = 0
        if live_overview:
            parsed = parse_live_overview(live_overview)
            duration_hours = 60.0 / 3600.0  # ~1 min aligned to collector
            price = await self._current_price(db, site.id, is_sqlite, site.fallback_purchase_price_sek_kwh)
            sample = _sample_from_parsed(parsed, price_sek_kwh=price, duration_hours=duration_hours)
            if sample is not None:
                await self._sampler.sample_site_ledger(db, site=site, sample=sample, is_sqlite=is_sqlite)

        charger_repo = EvChargerRepository(db)
        chargers = await charger_repo.list_for_site(site.id)
        for charger in chargers:
            if not charger.chargeamp_charger_id:
                continue
            try:
                processed += await self._process_charger(db, charger, site, live_overview, is_sqlite)
            except Exception:
                logger.exception("EV accounting failed charger_id=%s", charger.id)
        return processed

    async def _process_charger(
        self,
        db: AsyncSession,
        charger,
        site: SiteModel,
        live_overview: dict | None,
        is_sqlite: bool,
    ) -> int:
        cipher = CredentialCipher()
        api_key = cipher.decrypt(charger.chargeamps_api_key) or os.getenv("CHARGEAMPS_API_KEY", "")
        meter_adapter = ChargeAmpsMeterAdapter.build(
            charger.chargeamp_charger_id,
            api_key=api_key,
            phases=charger.phases,
            nominal_voltage_v=charger.nominal_voltage_v,
        )
        meter = await meter_adapter.get_snapshot()

        energy_sample = self._energy_sample_from_overview(live_overview, site, db, is_sqlite)
        await self._session_service.process_charger(db, charger=charger, site=site, meter=meter)
        if energy_sample is not None:
            await self._sampler.sample_active_session(
                db,
                charger=charger,
                site=site,
                meter=meter,
                energy_sample=energy_sample,
                is_sqlite=is_sqlite,
            )
        return 1

    def _energy_sample_from_overview(
        self,
        live_overview: dict | None,
        site: SiteModel,
        db: AsyncSession,
        is_sqlite: bool,
    ) -> SiteEnergySample | None:
        if not live_overview:
            return None
        parsed = parse_live_overview(live_overview)
        return _sample_from_parsed(
            parsed,
            price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            duration_hours=60.0 / 3600.0,
        )

    async def _current_price(
        self,
        db: AsyncSession,
        site_id: int,
        is_sqlite: bool,
        fallback: float,
    ) -> float:
        from datetime import UTC, datetime

        from energy_core.market_prices.currency import effective_price_sek_kwh

        repo = MarketPriceRepository(db, is_sqlite=is_sqlite)
        hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        row = await repo.get_at(site_id, hour)
        price_sek = effective_price_sek_kwh(row)
        if price_sek is not None:
            return price_sek
        return fallback
