"""Publisher trust key admin API."""

from __future__ import annotations

from datetime import datetime

from app.admin_audit_helpers import audit_admin_mutation
from app.user_auth import require_permission
from app.deps import get_db_session
from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel
from energy_core.platform.modules.packages.errors import PackageError, SIGNATURE_INVALID
from energy_core.platform.modules.packages.trust_store import PublisherKeyStatus
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/publishers", tags=["module-publishers"])


class PublisherKeyItem(BaseModel):
    publisher_id: str
    key_id: str
    status: str
    public_key_hex: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PublisherKeyCreateRequest(BaseModel):
    publisher_id: str = Field(min_length=1, max_length=128)
    key_id: str = Field(min_length=1, max_length=64)
    public_key_hex: str = Field(min_length=64, max_length=128)
    status: str = "trusted"


@router.get("", response_model=list[PublisherKeyItem])
async def list_publisher_keys(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("modules.manage")),
) -> list[PublisherKeyItem]:
    rows = (await session.scalars(select(ModulePublisherKeyModel).order_by(ModulePublisherKeyModel.publisher_id))).all()
    return [
        PublisherKeyItem(
            publisher_id=row.publisher_id,
            key_id=row.key_id,
            status=row.status,
            public_key_hex=row.public_key_hex,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _validate_public_key_hex(value: str) -> bytes:
    cleaned = value.strip().lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    try:
        raw = bytes.fromhex(cleaned)
    except ValueError as exc:
        raise PackageError("invalid public key hex", code=SIGNATURE_INVALID) from exc
    if len(raw) != 32:
        raise PackageError("Ed25519 public key must be 32 bytes", code=SIGNATURE_INVALID)
    return raw


@router.post("", response_model=PublisherKeyItem, status_code=status.HTTP_201_CREATED)
async def add_publisher_key(
    body: PublisherKeyCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("modules.manage")),
) -> PublisherKeyItem:
    _validate_public_key_hex(body.public_key_hex)
    if body.status not in {PublisherKeyStatus.TRUSTED, PublisherKeyStatus.REVOKED, PublisherKeyStatus.DISABLED}:
        raise HTTPException(status_code=422, detail={"code": "INVALID_STATUS", "message": "invalid publisher status"})
    existing = await session.scalar(
        select(ModulePublisherKeyModel).where(
            ModulePublisherKeyModel.publisher_id == body.publisher_id,
            ModulePublisherKeyModel.key_id == body.key_id,
        )
    )
    if existing is not None:
        if existing.status == PublisherKeyStatus.REVOKED.value:
            existing.public_key_hex = body.public_key_hex.strip().lower()
            existing.status = PublisherKeyStatus.TRUSTED.value
            await audit_admin_mutation(
                request,
                session,
                action="publisher.key_added",
                resource_type="module_publisher_key",
                resource_id=f"{body.publisher_id}:{body.key_id}",
                summary={"status": existing.status, "retrusted": True},
            )
            await session.commit()
            await session.refresh(existing)
            return PublisherKeyItem(
                publisher_id=existing.publisher_id,
                key_id=existing.key_id,
                status=existing.status,
                public_key_hex=existing.public_key_hex,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )
        raise HTTPException(status_code=409, detail={"code": "PUBLISHER_KEY_EXISTS", "message": "publisher key already exists"})
    row = ModulePublisherKeyModel(
        publisher_id=body.publisher_id,
        key_id=body.key_id,
        public_key_hex=body.public_key_hex.strip().lower(),
        status=body.status,
    )
    session.add(row)
    await audit_admin_mutation(
        request,
        session,
        action="publisher.key_added",
        resource_type="module_publisher_key",
        resource_id=f"{body.publisher_id}:{body.key_id}",
        summary={"status": body.status},
    )
    await session.commit()
    await session.refresh(row)
    return PublisherKeyItem(
        publisher_id=row.publisher_id,
        key_id=row.key_id,
        status=row.status,
        public_key_hex=row.public_key_hex,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/{publisher_id}/{key_id}/revoke", response_model=PublisherKeyItem)
async def revoke_publisher_key(
    publisher_id: str,
    key_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("modules.manage")),
) -> PublisherKeyItem:
    row = await session.scalar(
        select(ModulePublisherKeyModel).where(
            ModulePublisherKeyModel.publisher_id == publisher_id,
            ModulePublisherKeyModel.key_id == key_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Publisher key not found")
    row.status = PublisherKeyStatus.REVOKED.value
    await audit_admin_mutation(
        request,
        session,
        action="publisher.key_revoked",
        resource_type="module_publisher_key",
        resource_id=f"{publisher_id}:{key_id}",
    )
    await session.commit()
    await session.refresh(row)
    return PublisherKeyItem(
        publisher_id=row.publisher_id,
        key_id=row.key_id,
        status=row.status,
        public_key_hex=row.public_key_hex,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
