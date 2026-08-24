import logging
from datetime import UTC, datetime, timedelta

from app.api.energy_balance_helpers import snapshot_to_response
from app.deps import get_db_session
from app.schemas import (
    EnergyBalanceHistoryResponse,
    EnergyBalanceResponse,
    EnergyReasoningResponse,
    EvBridgeStatusResponse,
    EvChargerConnectionTestRequest,
    EvChargerControlRequest,
    EvChargerCreateRequest,
    EvChargerOverrideRequest,
    EvChargerResponse,
    EvChargerUpdateRequest,
    EvChargingSavingsResponse,
    ChargerConnectionTestResponse,
    SolarChargingPlanResponse,
    VirtualEvseStatusResponse,
)
from energy_core.charging.engine import bridge_status_from_charger
from energy_core.charging.reasoning import load_energy_reasoning_for_charger
from energy_core.energy.state import EnergyState
from energy_core.virtual_evse.from_charger import virtual_evse_state_from_charger
from energy_core.charging.solar_plan import load_solar_charging_plan_for_charger
from energy_core.charging.override import (
    ALLOWED_OVERRIDE_HOURS,
    override_active,
    override_until_from_hours,
)
from energy_core.charging.savings import compute_charging_savings
from energy_core.config import get_settings
from energy_core.chargers.framework.factory import ChargerAdapterFactory, configuration_from_model
from energy_core.chargers.framework.legacy_bridge import LegacyControlBridge
from energy_core.chargers.framework.meter_factory import MeterReaderFactory
from energy_core.chargers.framework.models import ChargerConfiguration
from energy_core.chargers.framework.catalog import CHARGE_AMPS_CLOUD, get_model
from energy_core.db.energy_balance_repo import EnergyBalanceRepository, SiteEnergyConfigRepository
from energy_core.db.ev_bridge_cycle_repo import EvBridgeCycleRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.heartbeat.ev_sync import HeartbeatEvSyncService
from energy_core.heartbeat_client import CHARGING_MODES
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["ev-chargers"])
logger = logging.getLogger(__name__)

CHARGING_MODE_VALUES = set(CHARGING_MODES)


async def _push_heartbeat_sync(session: AsyncSession, charger, site) -> None:
    try:
        await HeartbeatEvSyncService(session).push_charger(charger, site)
    except Exception:
        logger.exception("Heartbeat push failed for charger_id=%s", charger.id)


async def _enrich_charger(
    session: AsyncSession,
    charger,
    site_slug: str,
    *,
    include_power: bool = False,
) -> EvChargerResponse:
    base = EvChargerRepository.to_record(charger, site_slug)
    power_w = await _read_actual_power_w(charger) if include_power else None
    return _charger_response(
        base,
        available_modes=list(CHARGING_MODES),
        charging_mode=charger.charging_mode or base.charging_mode or "SMART_CHARGE",
        power_w=power_w,
    )


async def _read_actual_power_w(charger) -> float | None:
    meter = MeterReaderFactory.from_charger_model(charger)
    if meter is None:
        return None
    try:
        snapshot = await meter.get_snapshot()
        if snapshot.power_w is not None:
            return snapshot.power_w
        return None if snapshot.is_charging else 0.0
    except Exception as exc:
        logger.warning(
            "Could not read live charging power for charger_id=%s: %s",
            charger.id,
            type(exc).__name__,
        )
        return None


def _charger_response(base, **kwargs) -> EvChargerResponse:
    payload = {
        "id": base.id,
        "site_slug": base.site_slug,
        "name": base.name,
        "manufacturer": base.manufacturer,
        "model": base.model,
        "control_source": base.control_source,
        "heartbeat_ev_id": base.heartbeat_ev_id,
        "heartbeat_charger_id": base.heartbeat_charger_id,
        "chargeamp_charger_id": base.chargeamp_charger_id,
        "bridge_enabled": base.bridge_enabled,
        "max_current_a": base.max_current_a,
        "min_current_a": base.min_current_a,
        "phases": base.phases,
        "nominal_voltage_v": base.nominal_voltage_v,
        "max_power_w": base.max_power_w,
        "max_grid_import_w": base.max_grid_import_w,
        "update_interval_seconds": base.update_interval_seconds,
        "min_change_interval_seconds": base.min_change_interval_seconds,
        "current_hysteresis_a": base.current_hysteresis_a,
        "stale_timeout_seconds": base.stale_timeout_seconds,
        "chargeamps_api_key_configured": base.chargeamps_api_key_configured,
        "last_applied_current_a": base.last_applied_current_a,
        "last_bridge_run_at": base.last_bridge_run_at,
        "last_heartbeat_data_at": base.last_heartbeat_data_at,
        "override_until": base.override_until,
        "override_active": override_active(base.override_until),
        "charging_mode": base.charging_mode,
        "departure_time": base.departure_time,
        "target_soc_pct": base.target_soc_pct,
        "deadline_at": base.deadline_at,
        "solar_start_threshold_w": base.solar_start_threshold_w,
        "solar_stop_threshold_w": base.solar_stop_threshold_w,
        "solar_start_delay_seconds": base.solar_start_delay_seconds,
        "solar_stop_delay_seconds": base.solar_stop_delay_seconds,
        "last_charging_action": base.last_charging_action,
        "last_charging_reason": base.last_charging_reason,
        "last_charger_error_code": base.last_charger_error_code,
        "last_halo_connected": base.last_halo_connected,
        "last_vehicle_connected": base.last_vehicle_connected,
        "smart_charging_state": base.smart_charging_state,
        "last_requested_current_a": base.last_requested_current_a,
        "last_configured_current_a": base.last_configured_current_a,
        "last_actual_charging_current_a": base.last_actual_charging_current_a,
        "last_actual_power_w": base.last_actual_power_w,
        "externally_limited": base.externally_limited,
        "start_delay_seconds": base.start_delay_seconds,
        "stop_delay_seconds": base.stop_delay_seconds,
        "minimum_run_time_seconds": base.minimum_run_time_seconds,
        "minimum_off_time_seconds": base.minimum_off_time_seconds,
        "temporary_grid_import_allowance_w": base.temporary_grid_import_allowance_w,
        "temporary_grid_import_seconds": base.temporary_grid_import_seconds,
        "grid_deadband_w": base.grid_deadband_w,
        "minimum_current_change_interval_seconds": base.minimum_current_change_interval_seconds,
        "max_current_increase_per_step_a": base.max_current_increase_per_step_a,
        "max_current_decrease_per_step_a": base.max_current_decrease_per_step_a,
        "max_automatic_starts_per_hour": base.max_automatic_starts_per_hour,
        "virtual_evse_enabled": base.virtual_evse_enabled,
        "semp_device_id": base.semp_device_id,
        "manufacturer_id": base.manufacturer_id,
        "model_id": base.model_id,
        "integration_method": base.integration_method,
        "external_charger_id": base.external_charger_id,
        "connection_settings": base.connection_settings or {},
        "connection_status": base.connection_status,
        "last_connection_at": base.last_connection_at,
        "last_connection_test_at": base.last_connection_test_at,
        "heartbeat_sync_enabled": base.heartbeat_sync_enabled,
        "heartbeat_last_pushed_at": base.heartbeat_last_pushed_at,
        "heartbeat_last_pulled_at": base.heartbeat_last_pulled_at,
        "heartbeat_remote_updated_at": base.heartbeat_remote_updated_at,
        "heartbeat_sync_error": base.heartbeat_sync_error,
    }
    payload.update(kwargs)
    if payload.get("charging_mode") is None:
        payload["charging_mode"] = "SMART_CHARGE"
    return EvChargerResponse(**payload)


def _connection_test_response(result) -> ChargerConnectionTestResponse:
    detected = result.detected_device
    caps = result.capabilities
    return ChargerConnectionTestResponse(
        success=result.success,
        status=result.status,
        message=result.message,
        model_mismatch=result.model_mismatch,
        detected_device=(
            {
                "vendor": detected.vendor,
                "model": detected.model,
                "serial_number": detected.serial_number,
                "firmware": detected.firmware,
            }
            if detected
            else None
        ),
        capabilities=_capabilities_payload(caps) if caps else None,
    )


def _capabilities_payload(caps) -> dict[str, object]:
    return {
        "can_read_status": caps.can_read_status,
        "can_start_charging": caps.can_start_charging,
        "can_stop_charging": caps.can_stop_charging,
        "can_read_power": caps.can_read_power,
        "can_read_energy": caps.can_read_energy,
        "can_read_session": caps.can_read_session,
        "can_set_max_current": caps.can_set_max_current,
        "supports_smart_charging": caps.supports_smart_charging,
        "min_current_a": caps.min_current_a,
        "max_current_a": caps.max_current_a,
        "phases": caps.phases,
    }


def _framework_defaults(payload: EvChargerCreateRequest | EvChargerUpdateRequest) -> dict[str, object]:
    manufacturer_id = getattr(payload, "manufacturer_id", None)
    model_id = getattr(payload, "model_id", None)
    integration_method = getattr(payload, "integration_method", None)
    if manufacturer_id is None and model_id is None and integration_method is None:
        return {}
    manufacturer_id = manufacturer_id or "charge-amps"
    model_id = model_id or "halo"
    integration_method = integration_method or CHARGE_AMPS_CLOUD
    catalog_model = get_model(manufacturer_id, model_id)
    manufacturer = getattr(payload, "manufacturer", None) or (catalog_model and catalog_model.manufacturer_id) or "ChargeAmps"
    model = getattr(payload, "model", None) or (catalog_model and catalog_model.name) or "Halo"
    control_source = "chargeamp" if integration_method == CHARGE_AMPS_CLOUD else integration_method.lower()
    return {
        "manufacturer_id": manufacturer_id,
        "model_id": model_id,
        "integration_method": integration_method,
        "manufacturer": manufacturer if isinstance(manufacturer, str) else "ChargeAmps",
        "model": model if isinstance(model, str) else "Halo",
        "control_source": control_source,
    }


async def _run_connection_test(charger) -> ChargerConnectionTestResponse:
    adapter = LegacyControlBridge(ChargerAdapterFactory.from_charger_model(charger))
    result = await adapter.test_connection()
    return _connection_test_response(result)


async def _apply_connection_test_result(charger, result, session: AsyncSession) -> None:
    if result.success:
        charger.connection_status = "CONNECTED"
    elif result.status == "AUTH_FAILED":
        charger.connection_status = "ERROR"
    elif result.status == "UNSUPPORTED":
        charger.connection_status = "NOT_CONFIGURED"
    else:
        charger.connection_status = "DISCONNECTED"
    charger.last_connection_test_at = datetime.now(UTC)
    if result.success:
        charger.last_connection_at = charger.last_connection_test_at
    await session.commit()


@router.get("/sites/{slug}/ev-chargers", response_model=list[EvChargerResponse])
async def list_ev_chargers(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[EvChargerResponse]:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    chargers = await repo.list_for_site(site.id)
    return [await _enrich_charger(session, charger, slug, include_power=True) for charger in chargers]


@router.post("/sites/{slug}/ev-chargers", response_model=EvChargerResponse, status_code=status.HTTP_201_CREATED)
async def create_ev_charger(
    slug: str,
    payload: EvChargerCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EvChargerResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    framework = _framework_defaults(payload)
    control_source = framework.get("control_source", payload.control_source)
    if control_source not in ("chargeamp",) and not payload.integration_method:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid control_source")

    external_id = payload.external_charger_id or payload.chargeamp_charger_id
    charger = await repo.create(
        site.id,
        name=payload.name,
        manufacturer=str(framework.get("manufacturer", payload.manufacturer)),
        model=str(framework.get("model", payload.model)),
        control_source=str(control_source),
        heartbeat_ev_id=payload.heartbeat_ev_id,
        heartbeat_charger_id=payload.heartbeat_charger_id,
        chargeamp_charger_id=payload.chargeamp_charger_id,
        bridge_enabled=payload.bridge_enabled,
        max_current_a=payload.max_current_a,
        min_current_a=payload.min_current_a,
        phases=payload.phases,
        nominal_voltage_v=payload.nominal_voltage_v,
        max_power_w=payload.max_power_w,
        max_grid_import_w=payload.max_grid_import_w,
        update_interval_seconds=payload.update_interval_seconds,
        min_change_interval_seconds=payload.min_change_interval_seconds,
        current_hysteresis_a=payload.current_hysteresis_a,
        stale_timeout_seconds=payload.stale_timeout_seconds,
        chargeamps_api_key=payload.chargeamps_api_key,
        charging_mode=payload.charging_mode or "SMART_CHARGE",
        departure_time=payload.departure_time,
        target_soc_pct=payload.target_soc_pct,
        deadline_at=payload.deadline_at,
        solar_start_threshold_w=payload.solar_start_threshold_w or 1500.0,
        solar_stop_threshold_w=payload.solar_stop_threshold_w or 800.0,
        solar_start_delay_seconds=payload.solar_start_delay_seconds or 30,
        solar_stop_delay_seconds=payload.solar_stop_delay_seconds or 60,
        start_delay_seconds=payload.start_delay_seconds or 120,
        stop_delay_seconds=payload.stop_delay_seconds or 300,
        minimum_run_time_seconds=payload.minimum_run_time_seconds or 300,
        minimum_off_time_seconds=payload.minimum_off_time_seconds or 300,
        temporary_grid_import_allowance_w=payload.temporary_grid_import_allowance_w or 800.0,
        temporary_grid_import_seconds=payload.temporary_grid_import_seconds or 180,
        grid_deadband_w=payload.grid_deadband_w or 300.0,
        minimum_current_change_interval_seconds=payload.minimum_current_change_interval_seconds or 30,
        max_current_increase_per_step_a=payload.max_current_increase_per_step_a or 1.0,
        max_current_decrease_per_step_a=payload.max_current_decrease_per_step_a or 2.0,
        max_automatic_starts_per_hour=payload.max_automatic_starts_per_hour or 4,
        manufacturer_id=framework.get("manufacturer_id") or payload.manufacturer_id,
        model_id=framework.get("model_id") or payload.model_id,
        integration_method=framework.get("integration_method") or payload.integration_method,
        external_charger_id=external_id,
        connection_settings=payload.connection_settings,
    )
    await session.commit()
    return await _enrich_charger(session, charger, slug)


@router.post(
    "/sites/{slug}/ev-chargers/test-connection",
    response_model=ChargerConnectionTestResponse,
)
async def test_ev_charger_connection_draft(
    slug: str,
    payload: EvChargerConnectionTestRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChargerConnectionTestResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    external_id = payload.external_charger_id or payload.chargeamp_charger_id
    config = ChargerConfiguration(
        charger_id=0,
        site_id=site.id,
        manufacturer_id=payload.manufacturer_id,
        model_id=payload.model_id,
        integration_method=payload.integration_method,
        display_name="connection-test",
        enabled=True,
        external_charger_id=external_id,
        api_key=payload.chargeamps_api_key,
        connection_settings=dict(payload.connection_settings),
        min_current_a=payload.min_current_a,
        max_current_a=payload.max_current_a,
        phases=payload.phases,
        nominal_voltage_v=payload.nominal_voltage_v,
    )
    adapter = LegacyControlBridge(ChargerAdapterFactory.create(config))
    result = await adapter.test_connection()
    return _connection_test_response(result)


@router.post(
    "/sites/{slug}/ev-chargers/{charger_id}/test-connection",
    response_model=ChargerConnectionTestResponse,
)
async def test_ev_charger_connection(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ChargerConnectionTestResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    adapter = LegacyControlBridge(ChargerAdapterFactory.from_charger_model(charger))
    raw = await adapter.test_connection()
    await _apply_connection_test_result(charger, raw, session)
    return _connection_test_response(raw)


@router.put("/sites/{slug}/ev-chargers/{charger_id}", response_model=EvChargerResponse)
async def update_ev_charger(
    slug: str,
    charger_id: int,
    payload: EvChargerUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EvChargerResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    charger = await repo.update(
        charger,
        name=payload.name,
        manufacturer=payload.manufacturer,
        model=payload.model,
        heartbeat_ev_id=payload.heartbeat_ev_id,
        heartbeat_charger_id=payload.heartbeat_charger_id,
        chargeamp_charger_id=payload.chargeamp_charger_id,
        bridge_enabled=payload.bridge_enabled,
        max_current_a=payload.max_current_a,
        min_current_a=payload.min_current_a,
        phases=payload.phases,
        nominal_voltage_v=payload.nominal_voltage_v,
        max_power_w=payload.max_power_w,
        max_grid_import_w=payload.max_grid_import_w,
        update_interval_seconds=payload.update_interval_seconds,
        min_change_interval_seconds=payload.min_change_interval_seconds,
        current_hysteresis_a=payload.current_hysteresis_a,
        stale_timeout_seconds=payload.stale_timeout_seconds,
        chargeamps_api_key=payload.chargeamps_api_key,
        clear_chargeamps_api_key=payload.clear_chargeamps_api_key,
        charging_mode=payload.charging_mode,
        departure_time=payload.departure_time,
        clear_departure_time=payload.clear_departure_time,
        target_soc_pct=payload.target_soc_pct,
        deadline_at=payload.deadline_at,
        clear_deadline_at=payload.clear_deadline_at,
        solar_start_threshold_w=payload.solar_start_threshold_w,
        solar_stop_threshold_w=payload.solar_stop_threshold_w,
        solar_start_delay_seconds=payload.solar_start_delay_seconds,
        solar_stop_delay_seconds=payload.solar_stop_delay_seconds,
        start_delay_seconds=payload.start_delay_seconds,
        stop_delay_seconds=payload.stop_delay_seconds,
        minimum_run_time_seconds=payload.minimum_run_time_seconds,
        minimum_off_time_seconds=payload.minimum_off_time_seconds,
        temporary_grid_import_allowance_w=payload.temporary_grid_import_allowance_w,
        temporary_grid_import_seconds=payload.temporary_grid_import_seconds,
        grid_deadband_w=payload.grid_deadband_w,
        minimum_current_change_interval_seconds=payload.minimum_current_change_interval_seconds,
        max_current_increase_per_step_a=payload.max_current_increase_per_step_a,
        max_current_decrease_per_step_a=payload.max_current_decrease_per_step_a,
        max_automatic_starts_per_hour=payload.max_automatic_starts_per_hour,
        virtual_evse_enabled=payload.virtual_evse_enabled,
        manufacturer_id=payload.manufacturer_id,
        model_id=payload.model_id,
        integration_method=payload.integration_method,
        external_charger_id=payload.external_charger_id,
        connection_settings=payload.connection_settings,
        heartbeat_sync_enabled=payload.heartbeat_sync_enabled,
    )
    await session.commit()
    if payload.heartbeat_sync_enabled or any(
        value is not None
        for value in (
            payload.charging_mode,
            payload.departure_time,
            payload.target_soc_pct,
        )
    ):
        await _push_heartbeat_sync(session, charger, site)
        await session.commit()
    return await _enrich_charger(session, charger, slug)


@router.delete("/sites/{slug}/ev-chargers/{charger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ev_charger(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    await repo.delete(charger)
    await session.commit()


@router.post("/sites/{slug}/ev-chargers/sync", response_model=list[EvChargerResponse])
async def sync_ev_chargers_from_heartbeat(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[EvChargerResponse]:
    from energy_core.heartbeat_client_factory import create_heartbeat_client

    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if not site.external_system_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Anläggningen saknar HeartBeat system-ID.",
        )

    client = await create_heartbeat_client(session)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="HeartBeat är inte konfigurerat (kräver molntjänst/lokal gateway med token).",
        )

    try:
        evs = await client.list_evs(site.external_system_id)
        wallboxes = await client.list_wallboxes(site.external_system_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    wallbox_by_ev = {
        str(box.get("assignedEvId")): box
        for box in wallboxes
        if box.get("assignedEvId")
    }

    existing = {c.heartbeat_ev_id: c for c in await repo.list_for_site(site.id) if c.heartbeat_ev_id}
    for ev in evs:
        ev_id = str(ev.get("id", ""))
        if not ev_id:
            continue
        profile = ev.get("profile") or {}
        wallbox = wallbox_by_ev.get(ev_id) or {}
        name = str(wallbox.get("name") or profile.get("name") or "Laddbox")
        manufacturer = str(profile.get("manufacturer") or "ChargeAmps")
        model = str(profile.get("model") or "Halo")
        charger_id = str(wallbox.get("gridxHardwareId") or ev.get("assignedChargerId") or "")

        if ev_id in existing:
            await repo.update(
                existing[ev_id],
                name=name,
                manufacturer=manufacturer,
                model=model,
                heartbeat_charger_id=charger_id or None,
                chargeamp_charger_id=charger_id or existing[ev_id].chargeamp_charger_id,
            )
        else:
            await repo.create(
                site.id,
                name=name,
                manufacturer=manufacturer,
                model=model,
                control_source="chargeamp",
                heartbeat_ev_id=ev_id,
                heartbeat_charger_id=charger_id or None,
                chargeamp_charger_id=charger_id or None,
                bridge_enabled=bool(charger_id),
                charging_mode="SMART_CHARGE",
            )

    await session.commit()
    chargers = await repo.list_for_site(site.id)
    return [await _enrich_charger(session, c, slug) for c in chargers]


@router.patch("/sites/{slug}/ev-chargers/{charger_id}/control", response_model=EvChargerResponse)
async def control_ev_charger(
    slug: str,
    charger_id: int,
    payload: EvChargerControlRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EvChargerResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    if payload.charging_mode and payload.charging_mode not in CHARGING_MODE_VALUES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid charging_mode")

    clear_override = payload.charging_mode == "PAUSED"
    await repo.update(
        charger,
        charging_mode=payload.charging_mode,
        departure_time=payload.departure_time,
        target_soc_pct=payload.target_soc_pct,
        deadline_at=payload.deadline_at,
        clear_deadline_at=payload.clear_deadline_at,
        clear_departure_time=payload.departure_time == "",
        clear_override=clear_override,
    )
    await session.commit()
    await _push_heartbeat_sync(session, charger, site)
    await session.commit()
    return await _enrich_charger(session, charger, slug)


@router.post("/sites/{slug}/ev-chargers/{charger_id}/override", response_model=EvChargerResponse)
async def set_ev_charger_override(
    slug: str,
    charger_id: int,
    payload: EvChargerOverrideRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EvChargerResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    if payload.clear:
        await repo.update(charger, clear_override=True)
    else:
        if payload.hours not in ALLOWED_OVERRIDE_HOURS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Override-tid måste vara 4, 8, 12 eller 24 timmar.",
            )
        until = override_until_from_hours(payload.hours)
        resume_mode = None
        if (charger.charging_mode or "").upper() == "PAUSED":
            resume_mode = "QUICK_CHARGE"
        await repo.update(
            charger,
            override_until=until,
            charging_mode=resume_mode,
        )

    await session.commit()
    await _push_heartbeat_sync(session, charger, site)
    await session.commit()
    return await _enrich_charger(session, charger, slug)


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/bridge-status",
    response_model=EvBridgeStatusResponse,
)
async def get_ev_charger_bridge_status(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> EvBridgeStatusResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    settings = get_settings()
    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    latest = await balance_repo.get_latest(site_id=site.id, charger_id=charger_id)
    balance = snapshot_to_response(latest, charger_id=charger_id) if latest else None

    energy: EnergyState | None = None
    if balance and balance.status != "UNAVAILABLE":
        energy = EnergyState(
            timestamp=balance.recorded_at or datetime.now(UTC),
            grid_import_w=balance.sungrow_grid_import_w,
            home_consumption_w=balance.heartbeat_home_consumption_w,
            ev_actual_power_w=balance.heartbeat_observed_ev_power_w,
        )

    status_record = bridge_status_from_charger(charger, site=site, energy=energy)

    return EvBridgeStatusResponse(
        charger_id=status_record.charger_id,
        bridge_enabled=status_record.bridge_enabled,
        charging_mode=status_record.charging_mode,
        active_policy=status_record.active_policy,
        ev_target_power_w=status_record.ev_target_power_w,
        requested_current_a=status_record.requested_current_a,
        applied_current_a=status_record.applied_current_a,
        previous_current_a=status_record.previous_current_a,
        configured_current_a=status_record.configured_current_a,
        actual_charging_current_a=status_record.actual_charging_current_a,
        actual_power_w=status_record.actual_power_w,
        smart_charging_state=status_record.smart_charging_state,
        externally_limited=status_record.externally_limited,
        display_status_sv=status_record.display_status_sv,
        fuse_headroom_a=status_record.fuse_headroom_a,
        last_heartbeat_data_at=status_record.last_heartbeat_data_at,
        last_bridge_run_at=status_record.last_bridge_run_at,
        halo_connected=status_record.halo_connected,
        vehicle_connected=status_record.vehicle_connected,
        decision_reason=status_record.decision_reason,
        discovery_hints=list(status_record.discovery_hints),
        stale=status_record.stale,
        override_active=status_record.override_active,
        override_until=status_record.override_until,
        last_error_code=status_record.last_error_code,
        last_charging_action=status_record.last_charging_action,
        phase_current_l1_a=status_record.phase_current_l1_a,
        phase_current_l2_a=status_record.phase_current_l2_a,
        phase_current_l3_a=status_record.phase_current_l3_a,
        sungrow_fresh=balance.sungrow_fresh if balance else None,
        sungrow_telemetry_age_seconds=balance.sungrow_telemetry_age_seconds if balance else None,
        energy_balance_status=balance.status if balance and balance.status != "UNAVAILABLE" else None,
        energy_balance_alignment_delta_seconds=balance.alignment_delta_seconds if balance else None,
        energy_balance_flags=balance.flags if balance else [],
    )


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/solar-charging-plan",
    response_model=SolarChargingPlanResponse,
)
async def get_ev_charger_solar_charging_plan(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SolarChargingPlanResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    plan = await load_solar_charging_plan_for_charger(session, site, charger)
    if plan is None:
        return SolarChargingPlanResponse(
            available=False,
            explanation_sv=(
                "Ange önskad energi (kWh) och avfärd eller deadline "
                "för solbaserad Smart-laddningsplanering."
            ),
        )

    return SolarChargingPlanResponse(
        available=True,
        expected_usable_solar_kwh=plan.expected_usable_solar_kwh,
        planning_solar_kwh=plan.planning_solar_kwh,
        solar_first=plan.solar_first,
        quality=plan.quality,
        confidence=plan.confidence,
        expected_solar_window_start=plan.expected_solar_window_start,
        expected_solar_window_end=plan.expected_solar_window_end,
        cheapest_grid_window=plan.cheapest_grid_window,
        explanation_sv=plan.explanation_sv,
        reason_code=plan.reason_code,
    )


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/savings",
    response_model=EvChargingSavingsResponse,
)
async def get_ev_charger_savings(
    slug: str,
    charger_id: int,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> EvChargingSavingsResponse:
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")

    period_to = datetime.now(UTC)
    period_from = period_to - timedelta(days=days)

    cycle_repo = EvBridgeCycleRepository(session)
    cycles = await cycle_repo.list_for_charger(charger_id, from_time=period_from, to_time=period_to)
    savings = compute_charging_savings(
        cycles,
        phases=charger.phases,
        nominal_voltage_v=charger.nominal_voltage_v,
    )

    return EvChargingSavingsResponse(
        charger_id=charger_id,
        period_from=period_from,
        period_to=period_to,
        energy_kwh=savings.energy_kwh,
        actual_cost_sek=savings.actual_cost_sek,
        baseline_cost_sek=savings.baseline_cost_sek,
        savings_sek=savings.savings_sek,
        savings_ore=savings.savings_ore,
        savings_pct=savings.savings_pct,
        charging_intervals=savings.charging_intervals,
        period_avg_price_kwh=savings.period_avg_price_kwh,
        has_data=savings.charging_intervals > 0,
    )


async def _get_site_charger(session: AsyncSession, slug: str, charger_id: int):
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")
    return site, charger


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/energy-reasoning",
    response_model=EnergyReasoningResponse,
)
async def get_energy_reasoning(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> EnergyReasoningResponse:
    site, charger = await _get_site_charger(session, slug, charger_id)
    snapshot = await load_energy_reasoning_for_charger(session, site, charger)
    payload = snapshot.to_dict()
    payload["charger_id"] = charger_id
    return EnergyReasoningResponse(**payload)


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/energy-balance",
    response_model=EnergyBalanceResponse,
)
async def get_energy_balance(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> EnergyBalanceResponse:
    site, _charger = await _get_site_charger(session, slug, charger_id)
    settings = get_settings()
    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    latest = await balance_repo.get_latest(site_id=site.id, charger_id=charger_id)
    return snapshot_to_response(latest, charger_id=charger_id)


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/energy-balance/history",
    response_model=EnergyBalanceHistoryResponse,
)
async def get_energy_balance_history(
    slug: str,
    charger_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> EnergyBalanceHistoryResponse:
    site, _charger = await _get_site_charger(session, slug, charger_id)
    settings = get_settings()
    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    rows = await balance_repo.list_history(
        site_id=site.id,
        charger_id=charger_id,
        limit=limit,
        offset=offset,
    )
    items = [snapshot_to_response(row, charger_id=charger_id) for row in rows]
    return EnergyBalanceHistoryResponse(items=items, total=len(items))


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/virtual-evse/status",
    response_model=VirtualEvseStatusResponse,
)
async def get_virtual_evse_status(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VirtualEvseStatusResponse:
    site, charger = await _get_site_charger(session, slug, charger_id)
    config_repo = SiteEnergyConfigRepository(session)
    site_config = await config_repo.get_or_create(site.id)
    settings = get_settings()
    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    latest = await balance_repo.get_latest(site_id=site.id, charger_id=charger_id)
    balance = snapshot_to_response(latest, charger_id=charger_id) if latest else None

    state = virtual_evse_state_from_charger(charger)
    heartbeat_detected = bool(
        balance and balance.heartbeat_observed_ev_power_w is not None
    )
    if state is not None:
        state = type(state)(
            device_id=state.device_id,
            recorded_at=state.recorded_at,
            status=state.status,
            reported_power_w=state.reported_power_w,
            vehicle_connected=state.vehicle_connected,
            halo_power_w=state.halo_power_w,
            stale=state.stale,
            heartbeat_detected=heartbeat_detected,
        )

    return VirtualEvseStatusResponse(
        charger_id=charger_id,
        virtual_evse_enabled=charger.virtual_evse_enabled,
        semp_device_id=charger.semp_device_id,
        status=state.status.value if state else None,
        reported_power_w=state.reported_power_w if state else None,
        halo_power_w=state.halo_power_w if state else charger.last_actual_power_w,
        heartbeat_observed_ev_power_w=balance.heartbeat_observed_ev_power_w if balance else None,
        heartbeat_detected=heartbeat_detected,
        vehicle_connected=state.vehicle_connected if state else charger.last_vehicle_connected,
        stale=state.stale if state else False,
        physical_charger_label=site_config.physical_ev_charger_label,
        ev_vehicle_label=site_config.ev_vehicle_label,
    )
