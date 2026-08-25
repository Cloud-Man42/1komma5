"""Admin endpoints for Apple device registration."""

from __future__ import annotations

from datetime import datetime

from app.deps import get_db_session
from app.widget_auth import WIDGET_METRICS
from energy_core.auth.device_tokens import generate_device_token
from energy_core.db.apple_device_repo import AppleDeviceRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/apple-devices", tags=["apple-devices"])


class AppleDeviceCreateRequest(BaseModel):
    owner_label: str = Field(min_length=1, max_length=128)
    device_name: str = Field(min_length=1, max_length=128)
    device_type: str = Field(default="iphone", min_length=1, max_length=64)
    default_site_slug: str | None = Field(default=None, max_length=64)


class AppleDeviceRenameRequest(BaseModel):
    device_name: str = Field(min_length=1, max_length=128)


class AppleDeviceResponse(BaseModel):
    id: int
    owner_label: str
    device_name: str
    device_type: str
    token_prefix: str
    scopes: str
    default_site_slug: str | None
    created_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None
    status: str


class AppleDeviceCreateResponse(AppleDeviceResponse):
    token: str


class AppleDeviceMetricsResponse(BaseModel):
    metrics: dict[str, float | int]


def _to_response(record, *, token: str | None = None) -> AppleDeviceResponse | AppleDeviceCreateResponse:
    payload = {
        "id": record.id,
        "owner_label": record.owner_label,
        "device_name": record.device_name,
        "device_type": record.device_type,
        "token_prefix": record.token_prefix,
        "scopes": record.scopes,
        "default_site_slug": record.default_site_slug,
        "created_at": record.created_at,
        "last_seen_at": record.last_seen_at,
        "revoked_at": record.revoked_at,
        "status": "active" if record.revoked_at is None else "revoked",
    }
    if token is not None:
        return AppleDeviceCreateResponse(**payload, token=token)
    return AppleDeviceResponse(**payload)


@router.get("", response_model=list[AppleDeviceResponse])
async def list_apple_devices(
    session: AsyncSession = Depends(get_db_session),
) -> list[AppleDeviceResponse]:
    repo = AppleDeviceRepository(session)
    records = await repo.list_all()
    return [_to_response(record) for record in records]


@router.post("", response_model=AppleDeviceCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_apple_device(
    payload: AppleDeviceCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AppleDeviceCreateResponse:
    repo = AppleDeviceRepository(session)
    generated = generate_device_token()
    record, token = await repo.create(
        owner_label=payload.owner_label.strip(),
        device_name=payload.device_name.strip(),
        device_type=payload.device_type.strip(),
        generated=generated,
        default_site_slug=payload.default_site_slug,
    )
    await session.commit()
    return _to_response(record, token=token)


@router.get("/metrics", response_model=AppleDeviceMetricsResponse)
async def apple_device_metrics(
    session: AsyncSession = Depends(get_db_session),
) -> AppleDeviceMetricsResponse:
    active = await AppleDeviceRepository(session).count_active()
    return AppleDeviceMetricsResponse(metrics=WIDGET_METRICS.to_dict(active))


@router.post("/{device_id}/revoke", response_model=AppleDeviceResponse)
async def revoke_apple_device(
    device_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> AppleDeviceResponse:
    repo = AppleDeviceRepository(session)
    record = await repo.revoke(device_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    await session.commit()
    return _to_response(record)


@router.patch("/{device_id}", response_model=AppleDeviceResponse)
async def rename_apple_device(
    device_id: int,
    payload: AppleDeviceRenameRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AppleDeviceResponse:
    repo = AppleDeviceRepository(session)
    record = await repo.rename(device_id, device_name=payload.device_name.strip())
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    await session.commit()
    return _to_response(record)
