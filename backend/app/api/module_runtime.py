"""Admin API for isolated runtime diagnostics (Step 5C.5) + pilot authorizations (Sprint E)."""

from __future__ import annotations

from datetime import datetime

from app.admin_auth import require_admin_token
from app.deps import get_app_settings, get_db_session
from energy_core.config import Settings
from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
from energy_core.platform.modules.runtime_authorization.service import RuntimeAuthorizationService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/runtime", tags=["module-runtime"])


class RuntimeSummary(BaseModel):
    id: int
    runtime_instance_id: str
    module_id: str
    version: str
    publisher_id: str
    artifact_sha256: str
    site_id: int
    state: str
    sandbox_mode: str | None = None
    process_identity: str | None = None
    last_error: str | None = None
    started_at: datetime | None = None


class RuntimeSecurityView(BaseModel):
    runtime_instance_id: str
    state: str
    artifact_sha256: str
    sandbox_mode: str | None = None
    runtime_blocked: bool = True
    third_party_runtime_enabled: bool = False
    control_isolation_gate_open: bool = False
    selective_authorization_available: bool = False
    message: str = "Runtime blocked pending isolation verification"


class RuntimeListResponse(BaseModel):
    runtimes: list[RuntimeSummary]
    runtime_blocked: bool = True
    selective_authorization_available: bool = False
    active_authorizations: int = 0
    message: str = "Runtime blocked pending isolation verification"


class RuntimeAuthorizationView(BaseModel):
    id: int
    module_id: str
    version: str
    artifact_sha256: str
    publisher_id: str
    site_id: int
    approved_by: str
    approved_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    reason: str | None = None
    active: bool = True


class GrantAuthorizationRequest(BaseModel):
    module_id: str = Field(..., min_length=1, max_length=128)
    version: str = Field(..., min_length=1, max_length=64)
    artifact_sha256: str = Field(..., min_length=64, max_length=128)
    publisher_id: str = Field(..., min_length=1, max_length=128)
    site_id: int = Field(..., ge=1)
    expires_at: datetime | None = None
    reason: str | None = Field(None, max_length=500)


def _summary(record) -> RuntimeSummary:
    return RuntimeSummary(
        id=record.id or 0,
        runtime_instance_id=record.runtime_instance_id,
        module_id=record.module_id,
        version=record.version,
        publisher_id=record.publisher_id,
        artifact_sha256=record.artifact_sha256,
        site_id=record.site_id,
        state=record.state.value,
        sandbox_mode=record.sandbox_mode,
        process_identity=record.process_identity,
        last_error=record.last_error,
        started_at=record.started_at,
    )


def _auth_view(record) -> RuntimeAuthorizationView:
    return RuntimeAuthorizationView(
        id=record.id,
        module_id=record.module_id,
        version=record.version,
        artifact_sha256=record.artifact_sha256,
        publisher_id=record.publisher_id,
        site_id=record.site_id,
        approved_by=record.approved_by,
        approved_at=record.approved_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
        reason=record.reason,
        active=record.active,
    )


@router.get("/authorizations", response_model=list[RuntimeAuthorizationView])
async def list_runtime_authorizations(
    include_revoked: bool = False,
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
):
    service = RuntimeAuthorizationService(session)
    records = await service.list_authorizations(include_revoked=include_revoked)
    return [_auth_view(r) for r in records]


@router.post("/authorizations", response_model=RuntimeAuthorizationView, status_code=status.HTTP_201_CREATED)
async def grant_runtime_authorization(
    body: GrantAuthorizationRequest,
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
):
    service = RuntimeAuthorizationService(session)
    try:
        record = await service.grant(
            module_id=body.module_id,
            version=body.version,
            artifact_sha256=body.artifact_sha256,
            publisher_id=body.publisher_id,
            site_id=body.site_id,
            approved_by="admin",
            expires_at=body.expires_at,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await session.commit()
    return _auth_view(record)


@router.delete("/authorizations/{auth_id}", response_model=RuntimeAuthorizationView)
async def revoke_runtime_authorization(
    auth_id: int,
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
):
    service = RuntimeAuthorizationService(session)
    record = await service.revoke(auth_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "authorization not found"})
    await session.commit()
    return _auth_view(record)


@router.get("", response_model=RuntimeListResponse)
async def list_runtimes(
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    records = await IsolatedRuntimeRepository(session).list_instances()
    auth_service = RuntimeAuthorizationService(session, settings)
    auths = await auth_service.list_authorizations(include_revoked=False)
    selective = len(auths) > 0
    global_enabled = settings.third_party_runtime_enabled
    return RuntimeListResponse(
        runtimes=[_summary(r) for r in records],
        runtime_blocked=not global_enabled and not selective,
        selective_authorization_available=selective,
        active_authorizations=len(auths),
        message="Global third-party runtime disabled; selective pilot authorizations active"
        if selective and not global_enabled
        else "Runtime blocked pending isolation verification",
    )


@router.get("/{runtime_instance_id}", response_model=RuntimeSummary)
async def get_runtime(
    runtime_instance_id: str,
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
):
    record = await IsolatedRuntimeRepository(session).get_by_instance_id(runtime_instance_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "runtime not found"})
    return _summary(record)


@router.get("/{runtime_instance_id}/security", response_model=RuntimeSecurityView)
async def get_runtime_security(
    runtime_instance_id: str,
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    record = await IsolatedRuntimeRepository(session).get_by_instance_id(runtime_instance_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "runtime not found"})
    auth_service = RuntimeAuthorizationService(session, settings)
    auths = await auth_service.list_authorizations(include_revoked=False)
    selective = len(auths) > 0
    global_enabled = settings.third_party_runtime_enabled
    return RuntimeSecurityView(
        runtime_instance_id=record.runtime_instance_id,
        state=record.state.value,
        artifact_sha256=record.artifact_sha256,
        sandbox_mode=record.sandbox_mode,
        runtime_blocked=not global_enabled and not selective,
        third_party_runtime_enabled=settings.third_party_runtime_enabled,
        control_isolation_gate_open=ModuleInstallPolicyEngine.CONTROL_ISOLATION_GATE_OPEN,
        selective_authorization_available=selective,
    )


@router.post("/{runtime_instance_id}/stop")
async def stop_runtime(
    runtime_instance_id: str,
    _admin=Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
):
    from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager

    manager = IsolatedModuleRuntimeManager(session, settings)
    record = await manager.get_runtime(runtime_instance_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "runtime not found"})
    await manager.stop_runtime(runtime_instance_id, reason="admin stop")
    await session.commit()
    return {"ok": True, "runtime_instance_id": runtime_instance_id, "state": "STOPPED"}
