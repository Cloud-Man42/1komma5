from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.schemas import (
    ChargeAmpsConfigResponse,
    ChargingReadinessResponse,
    ChargerReadinessIssueResponse,
    HeartbeatConfigResponse,
    HeartbeatConfigUpdateRequest,
    SiteHeartbeatMappingResponse,
    SpaReadinessResponse,
    VehicleReadinessResponse,
)
from energy_core.chargers.chargeamps_config import build_chargeamps_connection_info
from energy_core.charging.readiness import evaluate_charging_readiness
from energy_core.config import get_settings
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.heartbeat_auth import HeartbeatAuthError
from energy_core.heartbeat_config import build_heartbeat_connection_info
from energy_core.heartbeat_connection import HeartbeatConnectionType

router = APIRouter(tags=["system"])


def _to_response(repo_record, sites, info) -> HeartbeatConfigResponse:
    return HeartbeatConfigResponse(
        connection_type=info.connection_type,
        connection_type_label=info.connection_type_label,
        host=info.host,
        port=info.port,
        use_tls=info.use_tls,
        api_path=info.api_path,
        poll_interval_seconds=info.poll_interval_seconds,
        dashboard_refresh_seconds=repo_record.dashboard_refresh_seconds,
        api_url=info.api_url,
        username=info.username,
        password_configured=info.password_configured,
        api_token_configured=info.api_token_configured,
        connection_mode=info.connection_mode,
        contacting_component=info.contacting_component,
        implementation_status=info.implementation_status,
        notes=list(info.notes),
        sites=[
            SiteHeartbeatMappingResponse(
                slug=site.slug,
                name=site.name,
                external_system_id=site.external_system_id,
            )
            for site in sites
        ],
        updated_at=repo_record.updated_at,
        heartbeat_write_enabled=repo_record.heartbeat_write_enabled,
    )


@router.get("/system/heartbeat-config", response_model=HeartbeatConfigResponse)
async def get_heartbeat_config(session: AsyncSession = Depends(get_db_session)) -> HeartbeatConfigResponse:
    repo = HeartbeatSettingsRepository(session)
    record = await repo.get_record()
    sites = await repo.list_site_mappings()
    info = build_heartbeat_connection_info(record, sites)
    return _to_response(record, sites, info)


@router.get("/system/chargeamps-config", response_model=ChargeAmpsConfigResponse)
async def get_chargeamps_config(session: AsyncSession = Depends(get_db_session)) -> ChargeAmpsConfigResponse:
    repo = EvChargerRepository(session)
    charger_api_keys_configured = await repo.count_with_chargeamps_api_key()
    info = build_chargeamps_connection_info(
        charger_api_keys_configured=charger_api_keys_configured,
    )
    return ChargeAmpsConfigResponse(
        provider=info.provider,
        effective_provider=info.effective_provider,
        mock=info.mock,
        api_key_configured=info.api_key_configured,
        env_api_key_configured=info.env_api_key_configured,
        charger_api_keys_configured=info.charger_api_keys_configured,
        email_configured=info.email_configured,
        password_configured=info.password_configured,
        ready=info.ready,
        notes=list(info.notes),
    )


@router.get("/system/charging-readiness", response_model=ChargingReadinessResponse)
async def get_charging_readiness(session: AsyncSession = Depends(get_db_session)) -> ChargingReadinessResponse:
    repo = EvChargerRepository(session)
    chargers = await repo.list_bridge_enabled_with_sites()
    report = evaluate_charging_readiness(chargers)
    return ChargingReadinessResponse(
        ready=report.ready,
        chargeamps_ready=report.chargeamps_ready,
        active_bridge_chargers=report.active_bridge_chargers,
        issues=[
            ChargerReadinessIssueResponse(
                site_slug=issue.site_slug,
                charger_id=issue.charger_id,
                charger_name=issue.charger_name,
                code=issue.code,
                message=issue.message,
            )
            for issue in report.issues
        ],
        notes=list(report.notes),
    )


@router.put("/system/heartbeat-config", response_model=HeartbeatConfigResponse)
async def update_heartbeat_config(
    payload: HeartbeatConfigUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatConfigResponse:
    if payload.connection_type == HeartbeatConnectionType.LOCAL and not payload.host:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Host/IP krävs för lokal gateway.",
        )

    repo = HeartbeatSettingsRepository(session)
    password = payload.password if payload.password else None
    api_token = payload.api_token if payload.api_token else None

    record = await repo.update(
        connection_type=payload.connection_type.value,
        host=payload.host,
        port=payload.port,
        use_tls=payload.use_tls,
        api_path=payload.api_path,
        poll_interval_seconds=payload.poll_interval_seconds,
        dashboard_refresh_seconds=payload.dashboard_refresh_seconds,
        username=payload.username,
        password=password,
        api_token=api_token,
        heartbeat_write_enabled=payload.heartbeat_write_enabled,
    )

    for site_update in payload.sites:
        try:
            await repo.update_site_system_id(site_update.slug, site_update.external_system_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown site: {exc.args[0]}",
            ) from exc

    record = await repo.get_record()
    should_refresh_token = (
        payload.connection_type == HeartbeatConnectionType.CLOUD
        and (password or (record.username and record.password_configured))
    )
    if should_refresh_token:
        try:
            await repo.ensure_api_token(force=bool(password))
        except HeartbeatAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        record = await repo.get_record()

    sites = await repo.list_site_mappings()
    await session.commit()

    info = build_heartbeat_connection_info(record, sites)
    return _to_response(record, sites, info)


@router.get("/system/integrations/spa-readiness", response_model=SpaReadinessResponse)
async def get_spa_readiness(session: AsyncSession = Depends(get_db_session)) -> SpaReadinessResponse:
    settings = get_settings()
    if not settings.arctic_spa_enabled:
        return SpaReadinessResponse(enabled=False)
    repo = ConsumerRepository(session)
    rows = await repo.list_enabled_spa_consumers()
    online = 0
    errors = 0
    for consumer, _config, _site in rows:
        poll = await repo.get_poll_state(consumer.id)
        if poll and poll.last_success_at:
            online += 1
        if poll and poll.consecutive_failures > 0:
            errors += 1
    return SpaReadinessResponse(
        enabled=True,
        configured_sites=len(rows),
        online_sites=online,
        error_sites=errors,
    )


@router.get("/system/integrations/vehicle-readiness", response_model=VehicleReadinessResponse)
async def get_vehicle_readiness(session: AsyncSession = Depends(get_db_session)) -> VehicleReadinessResponse:
    repo = VehicleProviderRepository(session)
    rows = await repo.list_enabled()
    connected = 0
    degraded = 0
    for row, _site in rows:
        if row.connection_state == "CONNECTED":
            connected += 1
        elif row.connection_state in {"BACKOFF", "DEGRADED", "RECONNECTING"}:
            degraded += 1
    return VehicleReadinessResponse(
        enabled_sites=len(rows),
        connected_sites=connected,
        degraded_sites=degraded,
    )
