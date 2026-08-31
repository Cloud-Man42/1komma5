"""DB-only energy snapshot builder for widget clients."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.charging.engine import bridge_status_from_charger
from energy_core.energy.integration import integrate_site_energy
from energy_core.charging.policy import normalized_mode
from energy_core.charging.state_machine import SmartChargingState as EngineSmartChargingState
from energy_core.config import Settings
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EnergyReadingModel, MarketPriceModel, SiteModel
from energy_core.db.repositories import EnergyReadingRepository
from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.energy_state.decision_text import EnergyDecisionTextService
from energy_core.energy_state.models import (
    BatteryState,
    DataQuality,
    EnergySiteSnapshot,
    EvState,
    SmartChargingMode,
    SmartChargingState,
    SystemStatus,
    battery_state_text_sv,
    ev_state_text_sv,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_POWER_DEADBAND_W = 25.0
_BATTERY_FULL_SOC = 99.0
_EV_CHARGING_POWER_W = 25.0


@dataclass(frozen=True, slots=True)
class _TodayEnergy:
    solar_kwh: float | None
    house_kwh: float | None
    import_kwh: float | None
    export_kwh: float | None
    battery_charged_kwh: float | None
    battery_discharged_kwh: float | None


@dataclass(frozen=True, slots=True)
class _Savings:
    today_sek: float | None
    month_sek: float | None
    quality: DataQuality


def _w_to_kw(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value / 1000.0, 3)


def _derive_battery_state(
    *,
    soc: float | None,
    power_w: float | None,
) -> BatteryState:
    if soc is None and power_w is None:
        return BatteryState.UNAVAILABLE
    if soc is not None and soc >= _BATTERY_FULL_SOC and (power_w is None or abs(power_w) <= _POWER_DEADBAND_W):
        return BatteryState.FULL
    if power_w is None:
        return BatteryState.UNKNOWN
    if power_w > _POWER_DEADBAND_W:
        return BatteryState.CHARGING
    if power_w < -_POWER_DEADBAND_W:
        return BatteryState.DISCHARGING
    return BatteryState.IDLE


def _map_charging_mode(mode: str | None) -> SmartChargingMode | None:
    if not mode:
        return None
    normalized = normalized_mode(mode)
    mapping = {
        "PAUSED": SmartChargingMode.OFF,
        "QUICK_CHARGE": SmartChargingMode.MANUAL,
        "PRICE_CHARGE": SmartChargingMode.CHEAPEST,
        "SOLAR_CHARGE": SmartChargingMode.SOLAR_ONLY,
        "SMART_CHARGE": SmartChargingMode.SMART,
    }
    return mapping.get(normalized, SmartChargingMode.UNKNOWN)


def _map_smart_charging_state(
    *,
    reason: str | None,
    engine_state: str | None,
    charging: bool,
) -> SmartChargingState | None:
    if reason in {"waiting_for_export", "solar_forecast_wait", "export_hysteresis"}:
        return SmartChargingState.WAITING_FOR_SURPLUS
    if reason in {"smart_scheduled", "smart_wait_cheaper"}:
        return SmartChargingState.SCHEDULED
    if charging:
        return SmartChargingState.SMART
    if engine_state:
        try:
            parsed = EngineSmartChargingState(engine_state)
        except ValueError:
            return SmartChargingState.UNKNOWN
        if parsed in {
            EngineSmartChargingState.WAITING_TO_START,
            EngineSmartChargingState.COOLDOWN,
        }:
            return SmartChargingState.WAITING_FOR_SURPLUS
        if parsed == EngineSmartChargingState.PAUSED:
            return SmartChargingState.OFF
        if parsed == EngineSmartChargingState.FAULT:
            return SmartChargingState.UNKNOWN
    return None


def _map_ev_state(
    *,
    charger_available: bool,
    bridge_status,
    connection_status: str,
    power_w: float | None,
) -> EvState:
    if not charger_available:
        return EvState.UNAVAILABLE
    if connection_status == "ERROR" or bridge_status.smart_charging_state == "FAULT":
        return EvState.FAULTED
    if bridge_status.halo_connected is False:
        return EvState.UNAVAILABLE
    if bridge_status.vehicle_connected is False:
        return EvState.DISCONNECTED
    if (power_w or 0.0) >= _EV_CHARGING_POWER_W:
        return EvState.CHARGING
    engine_state = bridge_status.smart_charging_state
    if engine_state in {"PAUSED", "STOPPING"}:
        return EvState.PAUSED
    if engine_state in {"WAITING_TO_START", "COOLDOWN"}:
        return EvState.WAITING
    if engine_state in {"STARTING", "CHARGING_STABLE", "REDUCING", "WAITING_TO_STOP"}:
        return EvState.WAITING if (power_w or 0.0) < _EV_CHARGING_POWER_W else EvState.CHARGING
    if bridge_status.vehicle_connected:
        return EvState.CONNECTED
    return EvState.UNKNOWN


def _system_status(*, has_reading: bool, is_stale: bool, fault: bool) -> SystemStatus:
    if fault:
        return SystemStatus.FAULT
    if not has_reading:
        return SystemStatus.OFFLINE
    if is_stale:
        return SystemStatus.PARTIAL
    return SystemStatus.ONLINE


class EnergyStateService:
    """Build normalized snapshots from persisted EMIC state only."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)

    async def build_snapshot(
        self,
        site: SiteModel,
        *,
        prefetched_latest: EnergyReadingModel | None = None,
    ) -> EnergySiteSnapshot:
        latest_row = prefetched_latest
        if latest_row is None:
            latest_row = await self._get_latest_row(site.id)
        latest = self._reading_repo._to_record(latest_row, site.slug) if latest_row is not None else None
        now = datetime.now(UTC)

        updated_at: datetime | None = None
        data_age_seconds: int | None = None
        is_stale = True

        if latest is not None:
            updated_at = latest.recorded_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            data_age_seconds = max(0, int((now - updated_at.astimezone(UTC)).total_seconds()))
            is_stale = data_age_seconds > self._settings.widget_stale_seconds

        today = await self._compute_today_energy(site)
        savings = await self._compute_savings(site)
        price_spot, price_all_in = await self._latest_market_price(site.id)
        ev_data = await self._compute_ev(site, latest_row)

        solar_power_kw = _w_to_kw(latest.solar_production_w if latest else None)
        house_power_kw = _w_to_kw(latest.consumption_w if latest else None)
        grid_import_kw = _w_to_kw(latest.grid_import_w if latest else None)
        grid_export_kw = _w_to_kw(latest.grid_export_w if latest else None)
        grid_power_kw = None
        if latest is not None:
            grid_power_kw = round((latest.grid_import_w - latest.grid_export_w) / 1000.0, 3)

        battery_power_kw = _w_to_kw(latest.battery_power_w if latest else None)
        battery_soc = latest.battery_soc_pct if latest else None
        battery_state = _derive_battery_state(soc=battery_soc, power_w=latest.battery_power_w if latest else None)

        self_consumption = None
        self_sufficiency = None
        if today.solar_kwh is not None and today.solar_kwh > 0 and today.house_kwh is not None:
            self_consumed = min(today.solar_kwh, today.house_kwh)
            self_consumption = round(min(100.0, (self_consumed / today.solar_kwh) * 100.0), 1)
        if today.house_kwh is not None and today.house_kwh > 0 and today.solar_kwh is not None:
            self_consumed = min(today.solar_kwh, today.house_kwh)
            self_sufficiency = round(min(100.0, (self_consumed / today.house_kwh) * 100.0), 1)

        operating_mode = ev_data.charging_mode
        partial = EnergySiteSnapshot(
            site_id=site.id,
            site_slug=site.slug,
            site_name=site.name,
            timezone=site.timezone,
            solar_power_kw=solar_power_kw,
            solar_energy_today_kwh=today.solar_kwh,
            house_power_kw=house_power_kw,
            house_energy_today_kwh=today.house_kwh,
            grid_power_kw=grid_power_kw,
            grid_import_power_kw=grid_import_kw,
            grid_export_power_kw=grid_export_kw,
            grid_import_today_kwh=today.import_kwh,
            grid_export_today_kwh=today.export_kwh,
            battery_soc_percent=round(battery_soc, 1) if battery_soc is not None else None,
            battery_power_kw=battery_power_kw,
            battery_state=battery_state,
            battery_state_text_sv=battery_state_text_sv(battery_state),
            battery_energy_charged_today_kwh=today.battery_charged_kwh,
            battery_energy_discharged_today_kwh=today.battery_discharged_kwh,
            ev_state=ev_data.state,
            ev_state_text_sv=ev_state_text_sv(ev_data.state),
            ev_power_kw=ev_data.power_kw,
            ev_energy_today_kwh=ev_data.energy_today_kwh,
            current_electricity_price=price_spot,
            current_electricity_price_including_fees=price_all_in,
            saved_today_sek=savings.today_sek,
            saved_month_sek=savings.month_sek,
            economic_data_quality=savings.quality,
            self_consumption_percent=self_consumption,
            self_sufficiency_percent=self_sufficiency,
            operating_mode=operating_mode,
            decision_text="",
            smart_charging_mode=ev_data.smart_mode,
            smart_charging_state=ev_data.smart_state,
            smart_charging_decision_text=ev_data.smart_decision_text,
            system_status=_system_status(
                has_reading=latest is not None,
                is_stale=is_stale,
                fault=ev_data.state == EvState.FAULTED,
            ),
            updated_at=updated_at,
            data_age_seconds=data_age_seconds,
            is_stale=is_stale,
        )
        decision_text = EnergyDecisionTextService.build(partial)
        return replace(partial, decision_text=decision_text)

    async def _get_latest_row(self, site_id: int) -> EnergyReadingModel | None:
        stmt = (
            select(EnergyReadingModel)
            .where(EnergyReadingModel.site_id == site_id)
            .order_by(EnergyReadingModel.recorded_at.desc())
            .limit(1)
        )
        return await self._session.scalar(stmt)

    async def _get_latest_rows(self, site_ids: list[int]) -> dict[int, EnergyReadingModel]:
        if not site_ids:
            return {}
        latest_subq = (
            select(
                EnergyReadingModel.site_id,
                func.max(EnergyReadingModel.recorded_at).label("max_recorded_at"),
            )
            .where(EnergyReadingModel.site_id.in_(site_ids))
            .group_by(EnergyReadingModel.site_id)
            .subquery()
        )
        stmt = (
            select(EnergyReadingModel)
            .join(
                latest_subq,
                (EnergyReadingModel.site_id == latest_subq.c.site_id)
                & (EnergyReadingModel.recorded_at == latest_subq.c.max_recorded_at),
            )
        )
        rows = (await self._session.scalars(stmt)).all()
        return {row.site_id: row for row in rows}

    async def build_snapshots_batch(self, sites: list[SiteModel]) -> list[EnergySiteSnapshot]:
        if not sites:
            return []
        latest_rows = await self._get_latest_rows([site.id for site in sites])
        return [
            await self.build_snapshot(site, prefetched_latest=latest_rows.get(site.id))
            for site in sites
        ]

    async def _compute_today_energy(self, site: SiteModel) -> _TodayEnergy:
        zone = ZoneInfo(site.timezone)
        now_local = datetime.now(zone)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_local.astimezone(UTC)
        now_utc = now_local.astimezone(UTC)

        stmt = (
            select(
                EnergyReadingModel.recorded_at,
                EnergyReadingModel.solar_production_w,
                EnergyReadingModel.consumption_w,
                EnergyReadingModel.grid_import_w,
                EnergyReadingModel.grid_export_w,
                EnergyReadingModel.battery_power_w,
                EnergyReadingModel.battery_charge_w,
                EnergyReadingModel.battery_discharge_w,
            )
            .where(
                EnergyReadingModel.site_id == site.id,
                EnergyReadingModel.recorded_at >= start_utc,
                EnergyReadingModel.recorded_at <= now_utc,
            )
            .order_by(EnergyReadingModel.recorded_at)
        )
        readings = (await self._session.execute(stmt)).all()
        if len(readings) < 2:
            return _TodayEnergy(None, None, None, None, None, None)

        totals = integrate_site_energy(readings, include_battery=True)

        return _TodayEnergy(
            solar_kwh=round(totals.solar_kwh, 1),
            house_kwh=round(totals.consumption_kwh, 1),
            import_kwh=round(totals.import_kwh, 1),
            export_kwh=round(totals.export_kwh, 1),
            battery_charged_kwh=round(totals.battery_charged_kwh, 1),
            battery_discharged_kwh=round(totals.battery_discharged_kwh, 1),
        )

    async def _compute_savings(self, site: SiteModel) -> _Savings:
        zone = ZoneInfo(site.timezone)
        now_local = datetime.now(zone)
        start_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_month_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_day_utc = start_day_local.astimezone(UTC)
        start_month_utc = start_month_local.astimezone(UTC)
        now_utc = now_local.astimezone(UTC)

        day_stats = await self._reading_repo.list_financial_stats(
            site_id=site.id,
            period="day",
            timezone=site.timezone,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
            from_time=start_day_utc,
            to_time=now_utc + timedelta(seconds=1),
            sell_config=sell_price_config_from_site(site),
        )
        month_stats = await self._reading_repo.list_financial_stats(
            site_id=site.id,
            period="month",
            timezone=site.timezone,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
            from_time=start_month_utc,
            to_time=now_utc + timedelta(seconds=1),
            sell_config=sell_price_config_from_site(site),
        )

        today_key = now_local.strftime("%Y-%m-%d")
        month_key = now_local.strftime("%Y-%m")
        day_row = next((row for row in day_stats if row.period_start == today_key), None)
        month_row = next((row for row in month_stats if row.period_start == month_key), None)

        if day_row is None and month_row is None:
            return _Savings(None, None, DataQuality.UNAVAILABLE)

        quality = DataQuality.ESTIMATED
        if day_row is not None and day_row.market_priced_fraction >= 0.5:
            quality = DataQuality.MEASURED
        elif day_row is not None and day_row.market_priced_fraction > 0:
            quality = DataQuality.CALCULATED

        today_sek = None
        month_sek = None
        if day_row is not None:
            today_sek = round(day_row.solar_savings_sek + day_row.battery_savings_sek, 2)
        if month_row is not None:
            month_sek = round(month_row.solar_savings_sek + month_row.battery_savings_sek, 2)

        return _Savings(today_sek, month_sek, quality)

    async def _latest_market_price(self, site_id: int) -> tuple[float | None, float | None]:
        stmt = (
            select(MarketPriceModel)
            .where(MarketPriceModel.site_id == site_id)
            .order_by(MarketPriceModel.recorded_at.desc())
            .limit(1)
        )
        row = await self._session.scalar(stmt)
        if row is None:
            return None, None
        return row.spot_price_eur_kwh, row.all_in_price_eur_kwh

    async def _compute_ev(self, site: SiteModel, latest_row: EnergyReadingModel | None):
        @dataclass(frozen=True, slots=True)
        class _EvData:
            state: EvState
            power_kw: float | None
            energy_today_kwh: float | None
            charging_mode: str | None
            smart_mode: SmartChargingMode | None
            smart_state: SmartChargingState | None
            smart_decision_text: str | None

        repo = EvChargerRepository(self._session)
        chargers = await repo.list_for_site(site.id)
        if not chargers:
            return _EvData(
                EvState.UNAVAILABLE,
                None,
                None,
                None,
                None,
                None,
                None,
            )

        charger = next((item for item in chargers if item.bridge_enabled), chargers[0])
        bridge_status = bridge_status_from_charger(charger, site=site)
        ev_power_w = charger.last_actual_power_w
        if ev_power_w is None and latest_row is not None:
            ev_power_w = latest_row.ev_power_w

        state = _map_ev_state(
            charger_available=True,
            bridge_status=bridge_status,
            connection_status=charger.connection_status,
            power_w=ev_power_w,
        )
        smart_mode = _map_charging_mode(bridge_status.active_policy)
        smart_state = _map_smart_charging_state(
            reason=bridge_status.decision_reason,
            engine_state=bridge_status.smart_charging_state,
            charging=state == EvState.CHARGING,
        )
        smart_decision = bridge_status.display_status_sv if bridge_status.display_status_sv else None

        return _EvData(
            state=state,
            power_kw=_w_to_kw(ev_power_w),
            energy_today_kwh=None,
            charging_mode=bridge_status.active_policy,
            smart_mode=smart_mode,
            smart_state=smart_state,
            smart_decision_text=smart_decision,
        )
