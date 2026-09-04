from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_audit_helpers import audit_admin_mutation
from app.admin_auth import require_admin_token
from app.deps import get_app_settings, get_db_session
from app.schemas import (
    ChargeAmpsConfigResponse,
    ChargingReadinessResponse,
    ChargerReadinessIssueResponse,
    HeartbeatConfigResponse,
    HeartbeatConfigUpdateRequest,
    SiteHeartbeatMappingResponse,
    SpaReadinessResponse,
    TimescalePolicyStatusResponse,
    VehicleReadinessResponse,
)
from energy_core.chargers.chargeamps_config import build_chargeamps_connection_info
from energy_core.charging.readiness import evaluate_charging_readiness
from energy_core.config import get_settings
from energy_core.config import Settings
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


@router.get("/system/timescale-status", response_model=TimescalePolicyStatusResponse)
async def get_timescale_status(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_admin_token),
) -> TimescalePolicyStatusResponse:
    from energy_core.db.timescale_retention import inspect_timescale_policies

    payload = await inspect_timescale_policies(session, settings)
    compression = {
        key: {"compression_enabled": value["compression_enabled"], "policy": value["policy"]}
        for key, value in (payload.get("compression") or {}).items()
    }
    return TimescalePolicyStatusResponse(
        status=str(payload.get("status") or "unknown"),
        reason=payload.get("reason"),
        retention_enabled=bool(payload.get("retention_enabled")),
        compression_enabled=bool(payload.get("compression_enabled")),
        retention=dict(payload.get("retention") or {}),
        compression=compression,
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
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
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
    await audit_admin_mutation(
        request,
        session,
        action="system.heartbeat_config.update",
        resource_type="heartbeat_config",
        summary={
            "connection_type": payload.connection_type.value,
            "host": payload.host,
            "port": payload.port,
            "use_tls": payload.use_tls,
            "poll_interval_seconds": payload.poll_interval_seconds,
            "dashboard_refresh_seconds": payload.dashboard_refresh_seconds,
            "username": payload.username,
            "password_provided": payload.password is not None,
            "api_token_provided": payload.api_token is not None,
            "sites": [site.model_dump() for site in payload.sites],
        },
    )
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


@router.get("/system/performance")
async def get_performance_metrics(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    from energy_core.db.repositories import SiteRepository
    from energy_core.db.snapshot_repo import SiteLiveSnapshotRepository
    from energy_core.performance.provider_metrics import get_provider_metrics_store
    from energy_core.performance.store import get_performance_store

    from energy_core.performance.task_metrics import summarize_collector_tasks
    from energy_core.cache.service import cache_service_status_async

    store = get_performance_store()
    site_repo = SiteRepository(session)
    snapshot_repo = SiteLiveSnapshotRepository(session, is_sqlite=settings.is_sqlite)
    sites = await site_repo.list_all()
    ages_by_site_id = {row["site_id"]: row for row in await snapshot_repo.list_snapshot_ages()}
    site_snapshots = [
        {
            "site_slug": site.slug,
            "site_name": site.name,
            "age_seconds": ages_by_site_id.get(site.id, {}).get("age_seconds"),
            "freshness": ages_by_site_id.get(site.id, {}).get("freshness", "MISSING"),
            "generated_at": ages_by_site_id.get(site.id, {}).get("generated_at"),
        }
        for site in sites
    ]
    return {
        **store.summary(),
        "cache": {**store.cache_stats(), **await cache_service_status_async(settings)},
        "providers": get_provider_metrics_store().summary(),
        "site_snapshots": site_snapshots,
        "tasks": await summarize_collector_tasks(session),
    }
