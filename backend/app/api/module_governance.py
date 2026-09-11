"""Admin governance API (Step 5C.2)."""

from __future__ import annotations

from datetime import datetime

from app.admin_audit_helpers import audit_admin_mutation
from app.admin_auth import require_admin_token
from app.deps import get_app_settings, get_db_session
from energy_core.config import AppEnvironment, Settings
from energy_core.platform.modules.governance.break_glass import get_break_glass_store
from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
from energy_core.platform.modules.governance.ownership_repository import OwnershipRepository
from energy_core.platform.modules.governance.policy_repository import PolicyRepository, PolicyRepositoryError
from energy_core.platform.modules.governance.publisher_repository import PublisherGovernanceError, PublisherRepository
from energy_core.platform.modules.governance.transfer_repository import TransferRepository, TransferRepositoryError
from energy_core.platform.modules.governance.types import GovernanceErrorCode, PolicyAction, PublisherStatus
from energy_core.platform.modules.governance.verification_repository import VerificationRepository
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/governance", tags=["module-governance"])


class PublisherResponse(BaseModel):
    publisher_id: str
    display_name: str
    organization: str | None = None
    verified_domain: str | None = None
    tier: str
    status: str
    verified_at: datetime | None = None
    suspended_at: datetime | None = None
    revoked_at: datetime | None = None
    module_count: int = 0


class PublisherCreateRequest(BaseModel):
    publisher_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)
    tier: str = "ORG_APPROVED"
    organization: str | None = None
    verified_domain: str | None = None
    legal_name: str | None = None


class PublisherUpdateRequest(BaseModel):
    display_name: str | None = None
    organization: str | None = None
    verified_domain: str | None = None
    legal_name: str | None = None
    tier: str | None = None


class PolicyResponse(BaseModel):
    policy_scope: str
    policy_version: int
    allowed_tiers: list[str]
    publisher_allowlist: list[str]
    publisher_denylist: list[str]
    module_allowlist: list[str]
    module_denylist: list[str]
    blocked_permissions: list[str]
    control_module_policy: str
    break_glass_enabled: bool
    updated_by: str | None = None
    updated_at: datetime | None = None


class PolicyUpdateRequest(BaseModel):
    expected_version: int
    allowed_tiers: list[str] | None = None
    publisher_allowlist: list[str] | None = None
    publisher_denylist: list[str] | None = None
    module_allowlist: list[str] | None = None
    module_denylist: list[str] | None = None
    blocked_permissions: list[str] | None = None
    control_module_policy: str | None = None
    break_glass_enabled: bool | None = None


class PolicyImpactResponse(BaseModel):
    publishers_total: int
    publishers_affected: int
    modules_total: int
    modules_affected: int


class PolicyHistoryItem(BaseModel):
    id: int
    policy_scope: str
    policy_version: int
    snapshot_json: str
    updated_by: str | None = None
    created_at: datetime | None = None


class OwnershipResponse(BaseModel):
    module_id: str
    publisher_id: str
    protected: bool


class TransferRequest(BaseModel):
    module_id: str
    to_publisher_id: str
    reason: str | None = None


class TransferResponse(BaseModel):
    id: int
    module_id: str
    from_publisher_id: str
    to_publisher_id: str
    from_tier: str | None
    to_tier: str | None
    status: str
    requested_by: str
    approved_by: str | None = None
    reason: str | None = None
    requested_at: datetime | None = None
    approved_at: datetime | None = None
    effective_at: datetime | None = None


class EvaluateRequest(BaseModel):
    action: str = "INSTALL"
    module_id: str
    publisher_id: str
    permissions: list[str] = Field(default_factory=list)
    provided_capabilities: list[str] = Field(default_factory=list)
    break_glass_active: bool | None = None


class EvaluateResponse(BaseModel):
    decision: str
    reason_codes: list[str]
    publisher_tier: str | None = None
    publisher_status: str | None = None
    control_capable: bool = False
    policy_version: int = 0
    explanation: str = ""


class BreakGlassActivateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=512)
    expires_at: datetime


class BreakGlassStatusResponse(BaseModel):
    active: bool
    reason: str | None = None
    expires_at: datetime | None = None
    actor: str | None = None


def _publisher_response(row, module_count: int = 0) -> PublisherResponse:
    return PublisherResponse(
        publisher_id=row.publisher_id,
        display_name=row.display_name,
        organization=row.organization,
        verified_domain=row.verified_domain,
        tier=row.tier,
        status=row.status,
        verified_at=row.verified_at,
        suspended_at=row.suspended_at,
        revoked_at=row.revoked_at,
        module_count=module_count,
    )


def _policy_response(snapshot) -> PolicyResponse:
    return PolicyResponse(
        policy_scope=snapshot.policy_scope,
        policy_version=snapshot.policy_version,
        allowed_tiers=list(snapshot.allowed_tiers),
        publisher_allowlist=list(snapshot.publisher_allowlist),
        publisher_denylist=list(snapshot.publisher_denylist),
        module_allowlist=list(snapshot.module_allowlist),
        module_denylist=list(snapshot.module_denylist),
        blocked_permissions=list(snapshot.blocked_permissions),
        control_module_policy=snapshot.control_module_policy,
        break_glass_enabled=snapshot.break_glass_enabled,
        updated_by=snapshot.updated_by,
        updated_at=snapshot.updated_at,
    )


def _transfer_response(row) -> TransferResponse:
    return TransferResponse(
        id=row.id,
        module_id=row.module_id,
        from_publisher_id=row.from_publisher_id,
        to_publisher_id=row.to_publisher_id,
        from_tier=row.from_tier,
        to_tier=row.to_tier,
        status=row.status,
        requested_by=row.requested_by,
        approved_by=row.approved_by,
        reason=row.reason,
        requested_at=row.requested_at,
        approved_at=row.approved_at,
        effective_at=row.effective_at,
    )


def _governance_http(exc: Exception) -> HTTPException:
    if isinstance(exc, PublisherGovernanceError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        if exc.code == GovernanceErrorCode.PUBLISHER_NOT_FOUND:
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code == GovernanceErrorCode.POLICY_CONFLICT:
            status_code = status.HTTP_409_CONFLICT
        return HTTPException(status_code=status_code, detail={"code": exc.code.value, "message": str(exc)})
    if isinstance(exc, (PolicyRepositoryError, TransferRepositoryError)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        if exc.code == GovernanceErrorCode.POLICY_CONFLICT:
            status_code = status.HTTP_409_CONFLICT
        elif exc.code == GovernanceErrorCode.TRANSFER_NOT_FOUND:
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code in {
            GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            GovernanceErrorCode.PUBLISHER_REVOKED,
            GovernanceErrorCode.POLICY_DENIED,
        }:
            status_code = status.HTTP_403_FORBIDDEN
        return HTTPException(status_code=status_code, detail={"code": exc.code.value, "message": str(exc)})
    raise exc


@router.get("/publishers", response_model=list[PublisherResponse])
async def list_publishers(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[PublisherResponse]:
    publishers = PublisherRepository(session)
    ownership = OwnershipRepository(session)
    rows = await publishers.list_publishers()
    counts: dict[str, int] = {}
    for item in await ownership.list_all():
        counts[item.publisher_id] = counts.get(item.publisher_id, 0) + 1
    return [_publisher_response(row, counts.get(row.publisher_id, 0)) for row in rows]


@router.post("/publishers", response_model=PublisherResponse, status_code=status.HTTP_201_CREATED)
async def create_publisher(
    body: PublisherCreateRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    try:
        row = await repo.create(
            publisher_id=body.publisher_id,
            display_name=body.display_name,
            tier=body.tier,
            organization=body.organization,
            verified_domain=body.verified_domain,
            legal_name=body.legal_name,
        )
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="publisher.created",
        resource_type="module_publisher",
        resource_id=body.publisher_id,
        summary={"tier": body.tier},
    )
    await session.commit()
    return _publisher_response(row)


@router.get("/publishers/{publisher_id}", response_model=PublisherResponse)
async def get_publisher(
    publisher_id: str,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    try:
        row = await repo.get_or_raise(publisher_id)
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    count = len(await OwnershipRepository(session).list_for_publisher(publisher_id))
    return _publisher_response(row, count)


@router.patch("/publishers/{publisher_id}", response_model=PublisherResponse)
async def update_publisher(
    publisher_id: str,
    body: PublisherUpdateRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    try:
        row = await repo.update_fields(
            publisher_id,
            display_name=body.display_name,
            organization=body.organization,
            verified_domain=body.verified_domain,
            legal_name=body.legal_name,
            tier=body.tier,
        )
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="publisher.updated",
        resource_type="module_publisher",
        resource_id=publisher_id,
    )
    await session.commit()
    return _publisher_response(row)


@router.post("/publishers/{publisher_id}/verify", response_model=PublisherResponse)
async def verify_publisher(
    publisher_id: str,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    verifications = VerificationRepository(session)
    try:
        row = await repo.get_or_raise(publisher_id)
        await verifications.create_manual(publisher_id=publisher_id, verified_by="admin")
        row = await repo.verify_publisher(publisher_id, verified_by="admin")
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="publisher.verified",
        resource_type="module_publisher",
        resource_id=publisher_id,
    )
    await session.commit()
    return _publisher_response(row)


@router.post("/publishers/{publisher_id}/suspend", response_model=PublisherResponse)
async def suspend_publisher(
    publisher_id: str,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    try:
        row = await repo.transition_status(publisher_id, PublisherStatus.SUSPENDED.value)
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="publisher.suspended",
        resource_type="module_publisher",
        resource_id=publisher_id,
    )
    await session.commit()
    return _publisher_response(row)


@router.post("/publishers/{publisher_id}/reactivate", response_model=PublisherResponse)
async def reactivate_publisher(
    publisher_id: str,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    try:
        row = await repo.transition_status(publisher_id, PublisherStatus.ACTIVE.value)
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="publisher.reactivated",
        resource_type="module_publisher",
        resource_id=publisher_id,
    )
    await session.commit()
    return _publisher_response(row)


@router.post("/publishers/{publisher_id}/revoke", response_model=PublisherResponse)
async def revoke_publisher(
    publisher_id: str,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PublisherResponse:
    repo = PublisherRepository(session)
    try:
        row = await repo.transition_status(publisher_id, PublisherStatus.REVOKED.value)
    except PublisherGovernanceError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="publisher.revoked",
        resource_type="module_publisher",
        resource_id=publisher_id,
    )
    await session.commit()
    return _publisher_response(row)


@router.get("/policy", response_model=PolicyResponse)
async def get_policy(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PolicyResponse:
    repo = PolicyRepository(session)
    row = await repo.get_or_create()
    return _policy_response(PolicyRepository.to_snapshot(row))


@router.put("/policy", response_model=PolicyResponse)
async def update_policy(
    body: PolicyUpdateRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PolicyResponse:
    repo = PolicyRepository(session)
    try:
        row = await repo.update(
            expected_version=body.expected_version,
            updated_by="admin",
            allowed_tiers=body.allowed_tiers,
            publisher_allowlist=body.publisher_allowlist,
            publisher_denylist=body.publisher_denylist,
            module_allowlist=body.module_allowlist,
            module_denylist=body.module_denylist,
            blocked_permissions=body.blocked_permissions,
            control_module_policy=body.control_module_policy,
            break_glass_enabled=body.break_glass_enabled,
        )
    except PolicyRepositoryError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="organization_policy.updated",
        resource_type="module_installation_policy",
        resource_id="installation",
        summary={"policy_version": row.policy_version},
    )
    await session.commit()
    return _policy_response(PolicyRepository.to_snapshot(row))


@router.get("/policy/history", response_model=list[PolicyHistoryItem])
async def policy_history(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[PolicyHistoryItem]:
    rows = await PolicyRepository(session).list_history()
    return [
        PolicyHistoryItem(
            id=row.id,
            policy_scope=row.policy_scope,
            policy_version=row.policy_version,
            snapshot_json=row.snapshot_json,
            updated_by=row.updated_by,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/policy/impact", response_model=PolicyImpactResponse)
async def policy_impact(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> PolicyImpactResponse:
    summary = await PolicyRepository(session).impact_summary()
    return PolicyImpactResponse(**summary)


@router.get("/ownership", response_model=list[OwnershipResponse])
async def list_ownership(
    publisher_id: str | None = None,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> list[OwnershipResponse]:
    repo = OwnershipRepository(session)
    rows = await repo.list_for_publisher(publisher_id) if publisher_id else await repo.list_all()
    return [
        OwnershipResponse(module_id=row.module_id, publisher_id=row.publisher_id, protected=row.protected)
        for row in rows
    ]


@router.post("/ownership/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def request_transfer(
    body: TransferRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> TransferResponse:
    repo = TransferRepository(session)
    try:
        row = await repo.request_transfer(
            module_id=body.module_id,
            to_publisher_id=body.to_publisher_id,
            requested_by="admin",
            reason=body.reason,
        )
    except TransferRepositoryError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.transfer_requested",
        resource_type="module_ownership_transfer",
        resource_id=str(row.id),
        summary={"module_id": body.module_id, "to": body.to_publisher_id},
    )
    await session.commit()
    return _transfer_response(row)


@router.post("/ownership/transfers/{transfer_id}/approve", response_model=TransferResponse)
async def approve_transfer(
    transfer_id: int,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> TransferResponse:
    repo = TransferRepository(session)
    try:
        row = await repo.approve(transfer_id, approved_by="admin")
    except TransferRepositoryError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.transfer_approved",
        resource_type="module_ownership_transfer",
        resource_id=str(transfer_id),
    )
    await session.commit()
    return _transfer_response(row)


@router.post("/ownership/transfers/{transfer_id}/reject", response_model=TransferResponse)
async def reject_transfer(
    transfer_id: int,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> TransferResponse:
    repo = TransferRepository(session)
    try:
        row = await repo.reject(transfer_id, approved_by="admin")
    except TransferRepositoryError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.transfer_rejected",
        resource_type="module_ownership_transfer",
        resource_id=str(transfer_id),
    )
    await session.commit()
    return _transfer_response(row)


@router.post("/ownership/transfers/{transfer_id}/complete", response_model=TransferResponse)
async def complete_transfer(
    transfer_id: int,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> TransferResponse:
    repo = TransferRepository(session)
    try:
        row = await repo.complete(transfer_id)
    except TransferRepositoryError as exc:
        raise _governance_http(exc) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.transfer_completed",
        resource_type="module_ownership_transfer",
        resource_id=str(transfer_id),
        summary={"module_id": row.module_id, "to_publisher_id": row.to_publisher_id},
    )
    await session.commit()
    return _transfer_response(row)


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_policy(
    body: EvaluateRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> EvaluateResponse:
    try:
        action = PolicyAction(body.action.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_ACTION", "message": "invalid policy action"}) from exc
    service = GovernanceEvaluationService(session)
    result = await service.evaluate(
        action=action,
        module_id=body.module_id,
        publisher_id=body.publisher_id,
        permissions=tuple(body.permissions),
        provided_capabilities=tuple(body.provided_capabilities),
        marketplace_enabled=settings.marketplace_metadata_enabled,
        app_env_production=settings.app_env == AppEnvironment.PRODUCTION,
        break_glass_active=body.break_glass_active,
    )
    if result.decision.value == "DENY":
        await audit_admin_mutation(
            request,
            session,
            action="policy.denied",
            resource_type="module_policy_evaluation",
            resource_id=body.module_id,
            summary={"publisher_id": body.publisher_id, "reasons": list(result.reason_codes)},
        )
        await session.commit()
    return EvaluateResponse(
        decision=result.decision.value,
        reason_codes=list(result.reason_codes),
        publisher_tier=result.publisher_tier,
        publisher_status=result.publisher_status,
        control_capable=result.control_capable,
        policy_version=result.policy_version,
        explanation=result.explanation,
    )


@router.post("/break-glass/activate", response_model=BreakGlassStatusResponse)
async def activate_break_glass(
    body: BreakGlassActivateRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> BreakGlassStatusResponse:
    policy = await PolicyRepository(session).get_or_create()
    if not policy.break_glass_enabled:
        raise HTTPException(
            status_code=403,
            detail={"code": GovernanceErrorCode.POLICY_DENIED.value, "message": "Break-glass is disabled in policy"},
        )
    session_obj = get_break_glass_store().activate(reason=body.reason, expires_at=body.expires_at, actor="admin")
    await audit_admin_mutation(
        request,
        session,
        action="break_glass.activated",
        resource_type="break_glass",
        summary={"expires_at": body.expires_at.isoformat()},
    )
    await session.commit()
    return BreakGlassStatusResponse(
        active=True,
        reason=session_obj.reason,
        expires_at=session_obj.expires_at,
        actor=session_obj.actor,
    )


@router.get("/break-glass/status", response_model=BreakGlassStatusResponse)
async def break_glass_status(
    _: None = Depends(require_admin_token),
) -> BreakGlassStatusResponse:
    current = get_break_glass_store().current()
    if current is None:
        return BreakGlassStatusResponse(active=False)
    return BreakGlassStatusResponse(
        active=True,
        reason=current.reason,
        expires_at=current.expires_at,
        actor=current.actor,
    )
