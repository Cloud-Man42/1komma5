from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_audit_helpers import audit_admin_mutation
from app.user_auth import require_permission
from app.deps import get_db_session
from app.schemas.heartbeat_accounts import (
    HeartbeatAccountCreateRequest,
    HeartbeatAccountDiagnosticsResponse,
    HeartbeatAccountLinkSiteRequest,
    HeartbeatAccountLinkSiteResponse,
    HeartbeatAccountResponse,
    HeartbeatAccountTestConnectionResponse,
    HeartbeatAccountUpdateRequest,
    HeartbeatDiscoveryResponse,
    HeartbeatGlobalDiagnosticsAccount,
    HeartbeatGlobalDiagnosticsComparison,
    HeartbeatGlobalDiagnosticsResponse,
    HeartbeatInstallationResponse,
    HeartbeatProbeResult,
    HeartbeatSerialDiscoveryResponse,
)
from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.models import SiteModel
from energy_core.integrations.heartbeat.account_health import derive_account_health
from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.auth_probe import probe_heartbeat_credentials
from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType
from energy_core.integrations.heartbeat.discovery_service import (
    discover_account_installations,
    discover_serial_for_account,
    discover_system_id_for_serial,
)
from energy_core.integrations.heartbeat.gridx_client import GridXClient
from energy_core.integrations.heartbeat.gridx_diagnostics import run_gridx_diagnostics
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider
from energy_core.integrations.heartbeat.username_mask import mask_username

router = APIRouter(tags=["heartbeat-accounts"])


async def _linked_sites(session: AsyncSession, account_id: int) -> list[SiteModel]:
    return list(
        await session.scalars(select(SiteModel).where(SiteModel.heartbeat_account_id == account_id))
    )


async def _linked_site_context(session: AsyncSession, account_id: int) -> tuple[list[str], str | None, str | None]:
    sites = await _linked_sites(session, account_id)
    slugs = [site.slug for site in sites]
    system_id = None
    gateway_id = None
    for site in sites:
        resolved_system = HeartbeatAccountRepository.resolve_system_id(site)
        resolved_gateway = HeartbeatAccountRepository.resolve_gateway_id(site)
        if resolved_system and system_id is None:
            system_id = resolved_system
        if resolved_gateway and gateway_id is None:
            gateway_id = resolved_gateway
    return slugs, system_id, gateway_id


def _to_response(record, *, linked_sites: list[str] | None = None) -> HeartbeatAccountResponse:
    health = derive_account_health(
        is_enabled=record.is_enabled,
        password_configured=record.password_configured,
        username=record.username,
        last_authentication_error=record.last_authentication_error,
        last_successful_authentication_at=record.last_successful_authentication_at,
        last_successful_api_call_at=record.last_successful_api_call_at,
        linked_sites_count=len(linked_sites or []),
    )
    return HeartbeatAccountResponse(
        id=record.id,
        slug=record.slug,
        name=record.name,
        provider=record.provider,
        connection_type=record.connection_type,
        host=record.host,
        port=record.port,
        use_tls=record.use_tls,
        api_path=record.api_path,
        auth_domain=record.auth_domain,
        auth_realm=record.auth_realm,
        auth_client_id=record.auth_client_id,
        username_masked=mask_username(record.username),
        password_configured=record.password_configured,
        api_token_configured=record.api_token_configured,
        refresh_token_configured=record.refresh_token_configured,
        api_url=record.api_url,
        token_expires_at=record.token_expires_at,
        is_enabled=record.is_enabled,
        status=health.status.value,
        linked_sites=linked_sites or [],
        last_authentication_at=record.last_authentication_at,
        last_successful_authentication_at=record.last_successful_authentication_at,
        last_api_call_at=record.last_api_call_at,
        last_successful_api_call_at=record.last_successful_api_call_at,
        last_authentication_error=record.last_authentication_error,
        updated_at=record.updated_at,
    )


async def _authenticate_account(repo: HeartbeatAccountRepository, account_id: int, *, password: str | None = None) -> None:
    row = await repo.get_by_id(account_id)
    if row is None:
        raise KeyError(account_id)
    username = row.username
    probe_password = password
    if probe_password is None:
        probe_password, _, _ = await repo.get_secrets(account_id)
    if not username or not probe_password:
        raise HeartbeatAuthError("E-post och lösenord krävs.")
    probe = await probe_heartbeat_credentials(username, probe_password)
    await repo.apply_auth_probe(account_id, probe)
    await repo.record_api_call(account_id, success=probe.probe_ok)


@router.get("/system/heartbeat-accounts", response_model=list[HeartbeatAccountResponse])
async def list_heartbeat_accounts(session: AsyncSession = Depends(get_db_session)) -> list[HeartbeatAccountResponse]:
    repo = HeartbeatAccountRepository(session)
    records = await repo.list_accounts()
    responses: list[HeartbeatAccountResponse] = []
    for record in records:
        linked = [site.slug for site in await _linked_sites(session, record.id)]
        responses.append(_to_response(record, linked_sites=linked))
    return responses


@router.post("/system/heartbeat-accounts", response_model=HeartbeatAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_heartbeat_account(
    payload: HeartbeatAccountCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatAccountResponse:
    repo = HeartbeatAccountRepository(session)
    if await repo.get_by_slug(payload.slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Account slug already exists: {payload.slug}")
    if not payload.password.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password is required")
    try:
        probe = await probe_heartbeat_credentials(payload.username, payload.password)
    except HeartbeatAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    record = await repo.create(
        slug=payload.slug,
        name=payload.name,
        provider=probe.provider,
        connection_type=probe.connection_type,
        host=probe.host,
        port=probe.port,
        use_tls=probe.use_tls,
        api_path=probe.api_path,
        auth_domain=probe.auth_domain,
        auth_realm=probe.auth_realm,
        auth_client_id=probe.auth_client_id,
        username=payload.username,
        password=payload.password,
        is_enabled=payload.is_enabled,
    )
    await repo.apply_auth_probe(record.id, probe)
    await repo.record_api_call(record.id, success=probe.probe_ok)
    record = await repo.get_record(record.id)
    await audit_admin_mutation(
        request,
        session,
        action="heartbeat_account.create",
        resource_type="heartbeat_account",
        summary={"slug": payload.slug, "name": payload.name, "provider": probe.provider},
    )
    await session.commit()
    return _to_response(record)


@router.patch("/system/heartbeat-accounts/{account_id}", response_model=HeartbeatAccountResponse)
async def update_heartbeat_account(
    account_id: int,
    payload: HeartbeatAccountUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatAccountResponse:
    repo = HeartbeatAccountRepository(session)
    try:
        await repo.update(
            account_id,
            name=payload.name,
            username=payload.username,
            password=payload.password,
            is_enabled=payload.is_enabled,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found") from exc

    if payload.password and payload.password.strip():
        try:
            await _authenticate_account(repo, account_id, password=payload.password)
        except HeartbeatAuthError as exc:
            row = await repo.get_by_id(account_id)
            if row is not None:
                row.last_authentication_error = str(exc)[:512]
                await session.flush()
    elif payload.username:
        try:
            await repo.ensure_api_token(account_id, force=True)
        except HeartbeatAuthError:
            pass

    record = await repo.get_record(account_id)
    linked = [site.slug for site in await _linked_sites(session, account_id)]
    await audit_admin_mutation(
        request,
        session,
        action="heartbeat_account.update",
        resource_type="heartbeat_account",
        summary={"account_id": account_id},
    )
    await session.commit()
    return _to_response(record, linked_sites=linked)


@router.delete("/system/heartbeat-accounts/{account_id}", response_model=HeartbeatAccountResponse)
async def delete_heartbeat_account(
    account_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatAccountResponse:
    repo = HeartbeatAccountRepository(session)
    try:
        record = await repo.get_record(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found") from exc
    linked = await _linked_sites(session, account_id)
    if linked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account is linked to sites: {', '.join(site.slug for site in linked)}. Unlink first.",
        )
    record = await repo.disable_account(account_id)
    await audit_admin_mutation(
        request,
        session,
        action="heartbeat_account.disable",
        resource_type="heartbeat_account",
        summary={"account_id": account_id},
    )
    await session.commit()
    return _to_response(record)


@router.post(
    "/system/heartbeat-accounts/{account_id}/test-connection",
    response_model=HeartbeatAccountTestConnectionResponse,
)
async def test_heartbeat_account_connection(
    account_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatAccountTestConnectionResponse:
    repo = HeartbeatAccountRepository(session)
    try:
        record = await repo.get_record(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found") from exc

    connected = False
    probe_path = None
    visible = 0
    error = record.last_authentication_error
    try:
        await _authenticate_account(repo, account_id)
        record = await repo.get_record(account_id)
        report = await discover_account_installations(
            session,
            account_id,
            provider=record.provider,
            api_url=record.api_url,
        )
        connected = report.authentication_ok
        visible = len(report.installations)
        probe_path = report.raw_paths_probed[0] if report.raw_paths_probed else record.provider
        await repo.record_api_call(account_id, success=connected)
    except HeartbeatAuthError as exc:
        error = str(exc)
        row = await repo.get_by_id(account_id)
        if row is not None:
            row.last_authentication_error = str(exc)[:512]
            await session.flush()

    await session.commit()
    record = await repo.get_record(account_id)
    return HeartbeatAccountTestConnectionResponse(
        account_id=record.id,
        slug=record.slug,
        connected=connected,
        provider=record.provider,
        api_url=record.api_url,
        probe_path=probe_path,
        visible_installations=visible,
        last_authentication_error=error,
    )


@router.post(
    "/system/heartbeat-accounts/{account_id}/discover",
    response_model=HeartbeatDiscoveryResponse,
)
async def discover_heartbeat_account(
    account_id: int,
    serial: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatDiscoveryResponse:
    repo = HeartbeatAccountRepository(session)
    try:
        record = await repo.get_record(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found") from exc

    try:
        await repo.ensure_api_token(account_id)
        if serial and serial.strip():
            report = await discover_serial_for_account(
                session,
                account_id,
                serial.strip(),
                provider=record.provider,
                api_url=record.api_url,
            )
        else:
            report = await discover_account_installations(
                session,
                account_id,
                provider=record.provider,
                api_url=record.api_url,
            )
        await repo.record_api_call(account_id, success=report.authentication_ok)
    except HeartbeatAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await session.commit()
    return HeartbeatDiscoveryResponse(
        account_id=record.id,
        slug=record.slug,
        provider=record.provider,
        api_url=record.api_url,
        authentication_ok=report.authentication_ok,
        installations=[
            HeartbeatInstallationResponse(
                name=inst.name,
                system_id=inst.system_id,
                site_id=inst.site_id,
                asset_id=inst.asset_id,
                device_id=inst.device_id,
                gateway_id=inst.gateway_id,
                serial_number=inst.serial_number,
            )
            for inst in report.installations
        ],
        serial_matches=[
            HeartbeatSerialDiscoveryResponse(
                serial=match.serial,
                found=match.found,
                resolved_site_id=match.resolved_site_id,
                resolved_system_id=match.resolved_system_id,
                resolved_asset_id=match.resolved_asset_id,
                resolved_device_id=match.resolved_device_id,
            )
            for match in report.serial_matches
        ],
        paths_probed=list(report.raw_paths_probed),
    )


@router.post(
    "/system/heartbeat-accounts/{account_id}/link-site",
    response_model=HeartbeatAccountLinkSiteResponse,
)
async def link_heartbeat_account_site(
    account_id: int,
    payload: HeartbeatAccountLinkSiteRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatAccountLinkSiteResponse:
    repo = HeartbeatAccountRepository(session)
    if await repo.get_by_id(account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found")
    site = await session.scalar(select(SiteModel).where(SiteModel.slug == payload.site_slug))
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown site: {payload.site_slug}")

    site.heartbeat_account_id = account_id
    serial = (
        payload.heartbeat_serial_number.strip()
        if payload.heartbeat_serial_number is not None
        else site.heartbeat_serial_number
    )
    if payload.heartbeat_serial_number is not None:
        site.heartbeat_serial_number = serial or None

    system_id = payload.heartbeat_system_id.strip() if payload.heartbeat_system_id else None
    if not system_id and serial:
        try:
            discovery = await discover_system_id_for_serial(session, account_id, serial)
            if discovery.found and discovery.resolved_system_id:
                system_id = discovery.resolved_system_id
                if discovery.resolved_site_id and not payload.heartbeat_site_id:
                    site.heartbeat_site_id = discovery.resolved_site_id
                if discovery.resolved_asset_id and not payload.heartbeat_asset_id:
                    site.heartbeat_asset_id = discovery.resolved_asset_id
                if discovery.resolved_device_id and not payload.heartbeat_device_id:
                    site.heartbeat_device_id = discovery.resolved_device_id
        except HeartbeatAuthError:
            pass

    if system_id:
        conflict = await session.scalar(
            select(SiteModel).where(
                SiteModel.slug != site.slug,
                SiteModel.heartbeat_system_id == system_id,
            )
        )
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Heartbeat system-ID används redan av platsen {conflict.slug}",
            )
        site.heartbeat_system_id = system_id
        site.external_system_id = system_id

    if payload.heartbeat_gateway_id is not None:
        site.heartbeat_gateway_id = payload.heartbeat_gateway_id.strip() or None
    if payload.heartbeat_site_id is not None:
        site.heartbeat_site_id = payload.heartbeat_site_id.strip() or None
    if payload.heartbeat_asset_id is not None:
        site.heartbeat_asset_id = payload.heartbeat_asset_id.strip() or None
    if payload.heartbeat_device_id is not None:
        site.heartbeat_device_id = payload.heartbeat_device_id.strip() or None

    await audit_admin_mutation(
        request,
        session,
        action="heartbeat_account.link_site",
        resource_type="site",
        resource_id=site.slug,
        summary={"account_id": account_id, "site_slug": site.slug},
    )
    await session.commit()
    return HeartbeatAccountLinkSiteResponse(
        site_slug=site.slug,
        heartbeat_account_id=account_id,
        heartbeat_system_id=site.heartbeat_system_id,
        heartbeat_gateway_id=site.heartbeat_gateway_id,
        heartbeat_serial_number=site.heartbeat_serial_number,
        heartbeat_site_id=site.heartbeat_site_id,
        heartbeat_asset_id=site.heartbeat_asset_id,
        heartbeat_device_id=site.heartbeat_device_id,
    )


@router.get("/system/heartbeat-accounts/{account_id}/diagnostics", response_model=HeartbeatAccountDiagnosticsResponse)
async def heartbeat_account_diagnostics(
    account_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.read")),
) -> HeartbeatAccountDiagnosticsResponse:
    repo = HeartbeatAccountRepository(session)
    try:
        record = await repo.get_record(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found") from exc

    linked_sites, system_id, gateway_id = await _linked_site_context(session, account_id)
    health = derive_account_health(
        is_enabled=record.is_enabled,
        password_configured=record.password_configured,
        username=record.username,
        last_authentication_error=record.last_authentication_error,
        last_successful_authentication_at=record.last_successful_authentication_at,
        last_successful_api_call_at=record.last_successful_api_call_at,
        linked_sites_count=len(linked_sites),
    )
    probes: list[HeartbeatProbeResult] = []
    token_ok = False
    try:
        await repo.ensure_api_token(account_id)
        token_ok = True
        record = await repo.get_record(account_id)
        client = await create_heartbeat_client(session, account_id=account_id)
        if isinstance(client, GridXClient):
            report = await run_gridx_diagnostics(
                client,
                provider=record.provider,
                api_url=record.api_url or "",
                system_id=system_id,
                gateway_id=gateway_id,
            )
            token_ok = report.token_ok
            probes = [
                HeartbeatProbeResult(path=p.path, ok=p.ok, status_code=p.status_code, detail=p.detail)
                for p in report.probes
            ]
            await repo.record_api_call(account_id, success=token_ok)
        elif client is not None and system_id:
            try:
                overview = await client.fetch_live_overview(system_id)
                probes.append(
                    HeartbeatProbeResult(
                        path=f"/systems/{system_id}/live-overview",
                        ok=bool(overview),
                        status_code=200 if overview else None,
                    )
                )
                await repo.record_api_call(account_id, success=bool(overview))
            except Exception as exc:
                probes.append(
                    HeartbeatProbeResult(
                        path=f"/systems/{system_id}/live-overview",
                        ok=False,
                        detail=str(exc)[:200],
                    )
                )
                await repo.record_api_call(account_id, success=False)
    except HeartbeatAuthError:
        token_ok = False

    await session.commit()
    return HeartbeatAccountDiagnosticsResponse(
        account_id=record.id,
        slug=record.slug,
        name=record.name,
        provider=record.provider,
        status=health.status.value,
        api_url=record.api_url,
        system_id=system_id,
        gateway_id=gateway_id,
        token_ok=token_ok,
        token_expires_at=record.token_expires_at,
        last_authentication_error=record.last_authentication_error,
        linked_sites=linked_sites,
        probes=probes,
    )


@router.post(
    "/system/heartbeat-accounts/{account_id}/discover-serial/{serial}",
    response_model=HeartbeatSerialDiscoveryResponse,
)
async def discover_serial_for_account_route(
    account_id: int,
    serial: str,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.manage")),
) -> HeartbeatSerialDiscoveryResponse:
    repo = HeartbeatAccountRepository(session)
    if await repo.get_by_id(account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heartbeat account not found")
    try:
        result = await discover_system_id_for_serial(session, account_id, serial)
        await repo.record_api_call(account_id, success=result.found)
        await session.commit()
    except HeartbeatAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return HeartbeatSerialDiscoveryResponse(
        serial=result.serial,
        found=result.found,
        resolved_site_id=result.resolved_site_id,
        resolved_system_id=result.resolved_system_id,
        resolved_asset_id=result.resolved_asset_id,
        resolved_device_id=result.resolved_device_id,
    )


@router.get("/system/heartbeat/diagnostics", response_model=HeartbeatGlobalDiagnosticsResponse)
async def heartbeat_global_diagnostics(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("heartbeat.read")),
) -> HeartbeatGlobalDiagnosticsResponse:
    repo = HeartbeatAccountRepository(session)
    accounts_out: list[HeartbeatGlobalDiagnosticsAccount] = []
    api_urls: set[str] = set()
    providers: set[str] = set()

    for record in await repo.list_accounts():
        linked = await _linked_sites(session, record.id)
        linked_slugs = [site.slug for site in linked]
        health = derive_account_health(
            is_enabled=record.is_enabled,
            password_configured=record.password_configured,
            username=record.username,
            last_authentication_error=record.last_authentication_error,
            last_successful_authentication_at=record.last_successful_authentication_at,
            last_successful_api_call_at=record.last_successful_api_call_at,
            linked_sites_count=len(linked),
        )
        if record.api_url:
            api_urls.add(record.api_url)
        providers.add(record.provider)

        serial_number = None
        system_id = None
        gateway_id = None
        site_id = None
        asset_id = None
        device_id = None
        serial_match = None
        visible = 0

        if linked:
            primary = linked[0]
            serial_number = primary.heartbeat_serial_number
            system_id = HeartbeatAccountRepository.resolve_system_id(primary)
            gateway_id = HeartbeatAccountRepository.resolve_gateway_id(primary)
            site_id = primary.heartbeat_site_id
            asset_id = primary.heartbeat_asset_id
            device_id = primary.heartbeat_device_id

        auth_label = "OK" if record.last_successful_authentication_at and not record.last_authentication_error else (
            "FAILED" if record.last_authentication_error else "UNKNOWN"
        )

        try:
            report = await discover_account_installations(
                session,
                record.id,
                provider=record.provider,
                api_url=record.api_url,
            )
            visible = len(report.installations)
            if serial_number:
                from energy_core.integrations.heartbeat.serial_matcher import match_serial

                match = match_serial({"candidates": [inst.__dict__ for inst in report.installations]}, serial_number)
                if not match.found:
                    match = await discover_system_id_for_serial(session, record.id, serial_number)
                serial_match = "FOUND" if match.found else "NOT FOUND"
                if match.found:
                    system_id = system_id or match.resolved_system_id
                    site_id = site_id or match.resolved_site_id
                    asset_id = asset_id or match.resolved_asset_id
                    device_id = device_id or match.resolved_device_id
        except Exception:
            visible = 0

        accounts_out.append(
            HeartbeatGlobalDiagnosticsAccount(
                slug=record.slug,
                name=record.name,
                configured=record.password_configured and bool(record.username.strip()),
                authentication=auth_label,
                status=health.status.value,
                api_url=record.api_url,
                provider=record.provider,
                linked_sites=linked_slugs,
                visible_installations=visible,
                serial_number=serial_number,
                serial_match=serial_match,
                system_id=system_id,
                gateway_id=gateway_id,
                site_id=site_id,
                asset_id=asset_id,
                device_id=device_id,
            )
        )

    def tri_bool(values: set[str], *, yes_threshold: int = 1) -> str:
        if len(values) <= yes_threshold:
            return "YES" if len(values) == 1 and values else "UNKNOWN"
        return "NO"

    comparison = HeartbeatGlobalDiagnosticsComparison(
        same_api_server=tri_bool(api_urls),
        same_auth_mechanism=tri_bool(providers),
        same_response_schema="NO" if len(providers) > 1 else "YES" if providers else "UNKNOWN",
        separate_account_context="YES" if len(accounts_out) > 1 else "UNKNOWN",
        same_tenant="UNKNOWN",
    )
    return HeartbeatGlobalDiagnosticsResponse(accounts=accounts_out, comparison=comparison)
