"""Persistence for EV chargers linked to sites."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EvChargerModel, SiteModel


@dataclass(frozen=True, slots=True)
class EvChargerRecord:
    id: int
    site_slug: str
    name: str
    manufacturer: str
    model: str
    control_source: str
    heartbeat_ev_id: str | None
    heartbeat_charger_id: str | None
    chargeamp_charger_id: str | None
    bridge_enabled: bool = False
    max_current_a: float = 16.0
    min_current_a: float = 6.0
    phases: int = 3
    nominal_voltage_v: float = 230.0
    max_power_w: float | None = None
    max_grid_import_w: float | None = None
    update_interval_seconds: int = 30
    min_change_interval_seconds: int = 60
    current_hysteresis_a: float = 1.0
    stale_timeout_seconds: int = 120
    chargeamps_api_key_configured: bool = False
    last_applied_current_a: float | None = None
    last_bridge_run_at: datetime | None = None
    last_heartbeat_data_at: datetime | None = None
    override_until: datetime | None = None
    charging_mode: str | None = None
    departure_time: str | None = None
    target_soc_pct: float | None = None
    deadline_at: datetime | None = None
    load_priority: int = 40
    solar_start_threshold_w: float = 1000.0
    solar_stop_threshold_w: float = 600.0
    solar_start_delay_seconds: int = 15
    solar_stop_delay_seconds: int = 60
    last_charging_action: str | None = None
    last_charging_reason: str | None = None
    last_charger_error_code: str | None = None
    last_halo_connected: bool | None = None
    last_vehicle_connected: bool | None = None
    smart_charging_state: str | None = None
    last_requested_current_a: float | None = None
    last_configured_current_a: float | None = None
    last_actual_charging_current_a: float | None = None
    last_actual_power_w: float | None = None
    externally_limited: bool | None = None
    last_start_at: datetime | None = None
    last_stop_at: datetime | None = None
    start_delay_seconds: int = 120
    stop_delay_seconds: int = 300
    minimum_run_time_seconds: int = 300
    minimum_off_time_seconds: int = 300
    temporary_grid_import_allowance_w: float = 800.0
    temporary_grid_import_seconds: int = 180
    grid_deadband_w: float = 300.0
    minimum_current_change_interval_seconds: int = 30
    max_current_increase_per_step_a: float = 1.0
    max_current_decrease_per_step_a: float = 2.0
    max_automatic_starts_per_hour: int = 4
    virtual_evse_enabled: bool = False
    semp_device_id: str | None = None
    manufacturer_id: str | None = None
    model_id: str | None = None
    integration_method: str | None = None
    external_charger_id: str | None = None
    connection_settings: dict[str, object] | None = None
    connection_status: str = "NOT_CONFIGURED"
    last_connection_at: datetime | None = None
    last_connection_test_at: datetime | None = None


class EvChargerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_site(self, site_id: int) -> list[EvChargerModel]:
        result = await self._session.scalars(
            select(EvChargerModel).where(EvChargerModel.site_id == site_id).order_by(EvChargerModel.name)
        )
        return list(result)

    async def count_with_chargeamps_api_key(self) -> int:
        result = await self._session.scalars(
            select(EvChargerModel.id).where(EvChargerModel.chargeamps_api_key != "")
        )
        return len(list(result))

    async def get_by_id(self, charger_id: int) -> EvChargerModel | None:
        return await self._session.get(EvChargerModel, charger_id)

    async def create(
        self,
        site_id: int,
        *,
        name: str,
        manufacturer: str = "ChargeAmps",
        model: str = "Halo",
        control_source: str = "chargeamp",
        heartbeat_ev_id: str | None = None,
        heartbeat_charger_id: str | None = None,
        chargeamp_charger_id: str | None = None,
        bridge_enabled: bool = False,
        max_current_a: float = 16.0,
        min_current_a: float = 6.0,
        phases: int = 3,
        nominal_voltage_v: float = 230.0,
        max_power_w: float | None = None,
        max_grid_import_w: float | None = None,
        update_interval_seconds: int = 30,
        min_change_interval_seconds: int = 60,
        current_hysteresis_a: float = 1.0,
        stale_timeout_seconds: int = 120,
        chargeamps_api_key: str | None = None,
        charging_mode: str | None = None,
        departure_time: str | None = None,
        target_soc_pct: float | None = None,
        deadline_at: datetime | None = None,
        solar_start_threshold_w: float = 1000.0,
        solar_stop_threshold_w: float = 600.0,
        solar_start_delay_seconds: int = 15,
        solar_stop_delay_seconds: int = 60,
        start_delay_seconds: int = 120,
        stop_delay_seconds: int = 300,
        minimum_run_time_seconds: int = 300,
        minimum_off_time_seconds: int = 300,
        temporary_grid_import_allowance_w: float = 800.0,
        temporary_grid_import_seconds: int = 180,
        grid_deadband_w: float = 300.0,
        minimum_current_change_interval_seconds: int = 30,
        max_current_increase_per_step_a: float = 1.0,
        max_current_decrease_per_step_a: float = 2.0,
        max_automatic_starts_per_hour: int = 4,
        manufacturer_id: str | None = None,
        model_id: str | None = None,
        integration_method: str | None = None,
        external_charger_id: str | None = None,
        connection_settings: dict[str, object] | None = None,
        connection_status: str = "NOT_CONFIGURED",
    ) -> EvChargerModel:
        charger = EvChargerModel(
            site_id=site_id,
            name=name.strip(),
            manufacturer=manufacturer.strip() or "ChargeAmps",
            model=model.strip() or "Halo",
            control_source=control_source,
            heartbeat_ev_id=heartbeat_ev_id.strip() if heartbeat_ev_id else None,
            heartbeat_charger_id=heartbeat_charger_id.strip() if heartbeat_charger_id else None,
            chargeamp_charger_id=chargeamp_charger_id.strip() if chargeamp_charger_id else None,
            bridge_enabled=bridge_enabled,
            max_current_a=max_current_a,
            min_current_a=min_current_a,
            phases=phases,
            nominal_voltage_v=nominal_voltage_v,
            max_power_w=max_power_w,
            max_grid_import_w=max_grid_import_w,
            update_interval_seconds=update_interval_seconds,
            min_change_interval_seconds=min_change_interval_seconds,
            current_hysteresis_a=current_hysteresis_a,
            stale_timeout_seconds=stale_timeout_seconds,
            chargeamps_api_key=chargeamps_api_key or "",
            charging_mode=charging_mode,
            departure_time=departure_time.strip() if departure_time else None,
            target_soc_pct=target_soc_pct,
            deadline_at=deadline_at,
            solar_start_threshold_w=solar_start_threshold_w,
            solar_stop_threshold_w=solar_stop_threshold_w,
            solar_start_delay_seconds=solar_start_delay_seconds,
            solar_stop_delay_seconds=solar_stop_delay_seconds,
            start_delay_seconds=start_delay_seconds,
            stop_delay_seconds=stop_delay_seconds,
            minimum_run_time_seconds=minimum_run_time_seconds,
            minimum_off_time_seconds=minimum_off_time_seconds,
            temporary_grid_import_allowance_w=temporary_grid_import_allowance_w,
            temporary_grid_import_seconds=temporary_grid_import_seconds,
            grid_deadband_w=grid_deadband_w,
            minimum_current_change_interval_seconds=minimum_current_change_interval_seconds,
            max_current_increase_per_step_a=max_current_increase_per_step_a,
            max_current_decrease_per_step_a=max_current_decrease_per_step_a,
            max_automatic_starts_per_hour=max_automatic_starts_per_hour,
            manufacturer_id=manufacturer_id,
            model_id=model_id,
            integration_method=integration_method,
            external_charger_id=external_charger_id.strip() if external_charger_id else None,
            connection_settings=_serialize_connection_settings(connection_settings),
            connection_status=connection_status,
        )
        self._session.add(charger)
        await self._session.flush()
        return charger

    async def update(
        self,
        charger: EvChargerModel,
        *,
        name: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        control_source: str | None = None,
        heartbeat_ev_id: str | None = None,
        heartbeat_charger_id: str | None = None,
        chargeamp_charger_id: str | None = None,
        clear_heartbeat_ev_id: bool = False,
        clear_heartbeat_charger_id: bool = False,
        clear_chargeamp_charger_id: bool = False,
        bridge_enabled: bool | None = None,
        max_current_a: float | None = None,
        min_current_a: float | None = None,
        phases: int | None = None,
        nominal_voltage_v: float | None = None,
        max_power_w: float | None = None,
        max_grid_import_w: float | None = None,
        update_interval_seconds: int | None = None,
        min_change_interval_seconds: int | None = None,
        current_hysteresis_a: float | None = None,
        stale_timeout_seconds: int | None = None,
        chargeamps_api_key: str | None = None,
        clear_chargeamps_api_key: bool = False,
        override_until: datetime | None = None,
        clear_override: bool = False,
        charging_mode: str | None = None,
        departure_time: str | None = None,
        clear_departure_time: bool = False,
        target_soc_pct: float | None = None,
        deadline_at: datetime | None = None,
        clear_deadline_at: bool = False,
        load_priority: int | None = None,
        solar_start_threshold_w: float | None = None,
        solar_stop_threshold_w: float | None = None,
        solar_start_delay_seconds: int | None = None,
        solar_stop_delay_seconds: int | None = None,
        start_delay_seconds: int | None = None,
        stop_delay_seconds: int | None = None,
        minimum_run_time_seconds: int | None = None,
        minimum_off_time_seconds: int | None = None,
        temporary_grid_import_allowance_w: float | None = None,
        temporary_grid_import_seconds: int | None = None,
        grid_deadband_w: float | None = None,
        minimum_current_change_interval_seconds: int | None = None,
        max_current_increase_per_step_a: float | None = None,
        max_current_decrease_per_step_a: float | None = None,
        max_automatic_starts_per_hour: int | None = None,
        virtual_evse_enabled: bool | None = None,
        smart_charging_state: str | None = None,
        last_requested_current_a: float | None = None,
        last_configured_current_a: float | None = None,
        last_actual_charging_current_a: float | None = None,
        last_actual_power_w: float | None = None,
        externally_limited: bool | None = None,
        last_start_at: datetime | None = None,
        last_stop_at: datetime | None = None,
        manufacturer_id: str | None = None,
        model_id: str | None = None,
        integration_method: str | None = None,
        external_charger_id: str | None = None,
        connection_settings: dict[str, object] | None = None,
        connection_status: str | None = None,
        last_connection_at: datetime | None = None,
        last_connection_test_at: datetime | None = None,
    ) -> EvChargerModel:
        if name is not None:
            charger.name = name.strip()
        if manufacturer is not None:
            charger.manufacturer = manufacturer.strip() or "ChargeAmps"
        if model is not None:
            charger.model = model.strip() or "Halo"
        if control_source is not None:
            charger.control_source = control_source
        if heartbeat_ev_id is not None:
            charger.heartbeat_ev_id = heartbeat_ev_id.strip() or None
        elif clear_heartbeat_ev_id:
            charger.heartbeat_ev_id = None
        if heartbeat_charger_id is not None:
            charger.heartbeat_charger_id = heartbeat_charger_id.strip() or None
        elif clear_heartbeat_charger_id:
            charger.heartbeat_charger_id = None
        if chargeamp_charger_id is not None:
            charger.chargeamp_charger_id = chargeamp_charger_id.strip() or None
        elif clear_chargeamp_charger_id:
            charger.chargeamp_charger_id = None
        if bridge_enabled is not None:
            charger.bridge_enabled = bridge_enabled
        if max_current_a is not None:
            charger.max_current_a = max_current_a
        if min_current_a is not None:
            charger.min_current_a = min_current_a
        if phases is not None:
            charger.phases = phases
        if nominal_voltage_v is not None:
            charger.nominal_voltage_v = nominal_voltage_v
        if max_power_w is not None:
            charger.max_power_w = max_power_w
        if max_grid_import_w is not None:
            charger.max_grid_import_w = max_grid_import_w
        if update_interval_seconds is not None:
            charger.update_interval_seconds = update_interval_seconds
        if min_change_interval_seconds is not None:
            charger.min_change_interval_seconds = min_change_interval_seconds
        if current_hysteresis_a is not None:
            charger.current_hysteresis_a = current_hysteresis_a
        if stale_timeout_seconds is not None:
            charger.stale_timeout_seconds = stale_timeout_seconds
        if chargeamps_api_key is not None:
            charger.chargeamps_api_key = chargeamps_api_key
        elif clear_chargeamps_api_key:
            charger.chargeamps_api_key = ""
        if override_until is not None:
            charger.override_until = override_until
        elif clear_override:
            charger.override_until = None
        if charging_mode is not None:
            charger.charging_mode = charging_mode.strip() or None
        if departure_time is not None:
            charger.departure_time = departure_time.strip() or None
        elif clear_departure_time:
            charger.departure_time = None
        if target_soc_pct is not None:
            charger.target_soc_pct = target_soc_pct
        if deadline_at is not None:
            charger.deadline_at = deadline_at
        elif clear_deadline_at:
            charger.deadline_at = None
        if load_priority is not None:
            charger.load_priority = load_priority
        if solar_start_threshold_w is not None:
            charger.solar_start_threshold_w = solar_start_threshold_w
        if solar_stop_threshold_w is not None:
            charger.solar_stop_threshold_w = solar_stop_threshold_w
        if solar_start_delay_seconds is not None:
            charger.solar_start_delay_seconds = solar_start_delay_seconds
        if solar_stop_delay_seconds is not None:
            charger.solar_stop_delay_seconds = solar_stop_delay_seconds
        if start_delay_seconds is not None:
            charger.start_delay_seconds = start_delay_seconds
        if stop_delay_seconds is not None:
            charger.stop_delay_seconds = stop_delay_seconds
        if minimum_run_time_seconds is not None:
            charger.minimum_run_time_seconds = minimum_run_time_seconds
        if minimum_off_time_seconds is not None:
            charger.minimum_off_time_seconds = minimum_off_time_seconds
        if temporary_grid_import_allowance_w is not None:
            charger.temporary_grid_import_allowance_w = temporary_grid_import_allowance_w
        if temporary_grid_import_seconds is not None:
            charger.temporary_grid_import_seconds = temporary_grid_import_seconds
        if grid_deadband_w is not None:
            charger.grid_deadband_w = grid_deadband_w
        if minimum_current_change_interval_seconds is not None:
            charger.minimum_current_change_interval_seconds = minimum_current_change_interval_seconds
        if max_current_increase_per_step_a is not None:
            charger.max_current_increase_per_step_a = max_current_increase_per_step_a
        if max_current_decrease_per_step_a is not None:
            charger.max_current_decrease_per_step_a = max_current_decrease_per_step_a
        if max_automatic_starts_per_hour is not None:
            charger.max_automatic_starts_per_hour = max_automatic_starts_per_hour
        if virtual_evse_enabled is not None:
            charger.virtual_evse_enabled = virtual_evse_enabled
            if virtual_evse_enabled:
                charger.semp_device_id = charger.semp_device_id or f"emic-evse-{charger.id}"
                if charger.semp_endpoint_registered_at is None:
                    from datetime import UTC, datetime

                    charger.semp_endpoint_registered_at = datetime.now(UTC)
            else:
                charger.semp_device_id = None
                charger.semp_endpoint_registered_at = None
        if smart_charging_state is not None:
            charger.smart_charging_state = smart_charging_state
        if last_requested_current_a is not None:
            charger.last_requested_current_a = last_requested_current_a
        if last_configured_current_a is not None:
            charger.last_configured_current_a = last_configured_current_a
        if last_actual_charging_current_a is not None:
            charger.last_actual_charging_current_a = last_actual_charging_current_a
        if last_actual_power_w is not None:
            charger.last_actual_power_w = last_actual_power_w
        if externally_limited is not None:
            charger.externally_limited = externally_limited
        if last_start_at is not None:
            charger.last_start_at = last_start_at
        if last_stop_at is not None:
            charger.last_stop_at = last_stop_at
        if manufacturer_id is not None:
            charger.manufacturer_id = manufacturer_id.strip() or None
        if model_id is not None:
            charger.model_id = model_id.strip() or None
        if integration_method is not None:
            charger.integration_method = integration_method.strip() or None
        if external_charger_id is not None:
            charger.external_charger_id = external_charger_id.strip() or None
        if connection_settings is not None:
            charger.connection_settings = _serialize_connection_settings(connection_settings)
        if connection_status is not None:
            charger.connection_status = connection_status
        if last_connection_at is not None:
            charger.last_connection_at = last_connection_at
        if last_connection_test_at is not None:
            charger.last_connection_test_at = last_connection_test_at
        await self._session.flush()
        return charger

    async def list_bridge_enabled_with_sites(self) -> list[tuple[EvChargerModel, SiteModel]]:
        result = await self._session.execute(
            select(EvChargerModel, SiteModel)
            .join(SiteModel, EvChargerModel.site_id == SiteModel.id)
            .where(EvChargerModel.bridge_enabled.is_(True))
            .order_by(SiteModel.slug, EvChargerModel.name)
        )
        return list(result.all())

    async def delete(self, charger: EvChargerModel) -> None:
        await self._session.delete(charger)

    @staticmethod
    def to_record(charger: EvChargerModel, site_slug: str) -> EvChargerRecord:
        return EvChargerRecord(
            id=charger.id,
            site_slug=site_slug,
            name=charger.name,
            manufacturer=charger.manufacturer,
            model=charger.model,
            control_source=charger.control_source,
            heartbeat_ev_id=charger.heartbeat_ev_id,
            heartbeat_charger_id=charger.heartbeat_charger_id,
            chargeamp_charger_id=charger.chargeamp_charger_id,
            bridge_enabled=charger.bridge_enabled,
            max_current_a=charger.max_current_a,
            min_current_a=charger.min_current_a,
            phases=charger.phases,
            nominal_voltage_v=charger.nominal_voltage_v,
            max_power_w=charger.max_power_w,
            max_grid_import_w=charger.max_grid_import_w,
            update_interval_seconds=charger.update_interval_seconds,
            min_change_interval_seconds=charger.min_change_interval_seconds,
            current_hysteresis_a=charger.current_hysteresis_a,
            stale_timeout_seconds=charger.stale_timeout_seconds,
            chargeamps_api_key_configured=bool(charger.chargeamps_api_key),
            last_applied_current_a=charger.last_applied_current_a,
            last_bridge_run_at=charger.last_bridge_run_at,
            last_heartbeat_data_at=charger.last_heartbeat_data_at,
            override_until=charger.override_until,
            charging_mode=charger.charging_mode,
            departure_time=charger.departure_time,
            target_soc_pct=charger.target_soc_pct,
            deadline_at=charger.deadline_at,
            load_priority=charger.load_priority,
            solar_start_threshold_w=charger.solar_start_threshold_w,
            solar_stop_threshold_w=charger.solar_stop_threshold_w,
            solar_start_delay_seconds=charger.solar_start_delay_seconds,
            solar_stop_delay_seconds=charger.solar_stop_delay_seconds,
            last_charging_action=charger.last_charging_action,
            last_charging_reason=charger.last_charging_reason,
            last_charger_error_code=charger.last_charger_error_code,
            last_halo_connected=charger.last_halo_connected,
            last_vehicle_connected=charger.last_vehicle_connected,
            smart_charging_state=charger.smart_charging_state,
            last_requested_current_a=charger.last_requested_current_a,
            last_configured_current_a=charger.last_configured_current_a,
            last_actual_charging_current_a=charger.last_actual_charging_current_a,
            last_actual_power_w=charger.last_actual_power_w,
            externally_limited=charger.externally_limited,
            last_start_at=charger.last_start_at,
            last_stop_at=charger.last_stop_at,
            start_delay_seconds=charger.start_delay_seconds,
            stop_delay_seconds=charger.stop_delay_seconds,
            minimum_run_time_seconds=charger.minimum_run_time_seconds,
            minimum_off_time_seconds=charger.minimum_off_time_seconds,
            temporary_grid_import_allowance_w=charger.temporary_grid_import_allowance_w,
            temporary_grid_import_seconds=charger.temporary_grid_import_seconds,
            grid_deadband_w=charger.grid_deadband_w,
            minimum_current_change_interval_seconds=charger.minimum_current_change_interval_seconds,
            max_current_increase_per_step_a=charger.max_current_increase_per_step_a,
            max_current_decrease_per_step_a=charger.max_current_decrease_per_step_a,
            max_automatic_starts_per_hour=charger.max_automatic_starts_per_hour,
            virtual_evse_enabled=charger.virtual_evse_enabled,
            semp_device_id=charger.semp_device_id,
            manufacturer_id=charger.manufacturer_id,
            model_id=charger.model_id,
            integration_method=charger.integration_method,
            external_charger_id=charger.external_charger_id,
            connection_settings=_parse_connection_settings(charger.connection_settings),
            connection_status=charger.connection_status,
            last_connection_at=charger.last_connection_at,
            last_connection_test_at=charger.last_connection_test_at,
        )

    async def get_site_by_slug(self, slug: str) -> SiteModel | None:
        return await self._session.scalar(select(SiteModel).where(SiteModel.slug == slug))


def _serialize_connection_settings(settings: dict[str, object] | None) -> str | None:
    if not settings:
        return None
    return json.dumps(settings)


def _parse_connection_settings(raw: str | None) -> dict[str, object] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
