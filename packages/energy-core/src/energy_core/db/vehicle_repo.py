"""Repositories for vehicle integration persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    SiteModel,
    VehicleCapabilityModel,
    VehicleModel,
    VehicleProviderConnectionModel,
    VehicleStateHistoryModel,
    VehicleStateLatestModel,
)
from energy_core.secrets import SecretBox
from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle

HISTORY_MIN_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class VehicleConnectionRecord:
    id: int
    site_id: int
    provider: str
    enabled: bool
    region: str
    username: str
    password_configured: bool
    device_guid: str
    session_id: str
    connection_state: str
    commands_enabled: bool
    token_expires_at: datetime | None
    last_error: str
    last_error_at: datetime | None
    backoff_until: datetime | None
    blocked_since: datetime | None
    reconnect_count: int
    http_429_count: int
    decode_failure_count: int


@dataclass(frozen=True, slots=True)
class VehicleRecord:
    id: int
    site_id: int
    provider: str
    external_id: str
    vin: str | None
    manufacturer: str
    model: str
    display_name: str
    enabled: bool
    charger_id: int | None


class VehicleProviderRepository:
    def __init__(self, session: AsyncSession, *, secret_box: SecretBox | None = None) -> None:
        self._session = session
        self._secrets = secret_box or SecretBox.from_settings()

    async def get_for_site(self, site_id: int, provider: str = "mercedes") -> VehicleProviderConnectionModel | None:
        result = await self._session.execute(
            select(VehicleProviderConnectionModel).where(
                VehicleProviderConnectionModel.site_id == site_id,
                VehicleProviderConnectionModel.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_site_slug(self, slug: str, provider: str = "mercedes") -> tuple[SiteModel, VehicleProviderConnectionModel] | None:
        result = await self._session.execute(
            select(SiteModel, VehicleProviderConnectionModel)
            .join(
                VehicleProviderConnectionModel,
                VehicleProviderConnectionModel.site_id == SiteModel.id,
            )
            .where(SiteModel.slug == slug, VehicleProviderConnectionModel.provider == provider)
        )
        row = result.first()
        return None if row is None else (row[0], row[1])

    async def get_or_create(self, site_id: int, provider: str = "mercedes") -> VehicleProviderConnectionModel:
        existing = await self.get_for_site(site_id, provider)
        if existing is not None:
            return existing
        row = VehicleProviderConnectionModel(site_id=site_id, provider=provider)
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_enabled(self, provider: str = "mercedes") -> list[tuple[VehicleProviderConnectionModel, SiteModel]]:
        result = await self._session.execute(
            select(VehicleProviderConnectionModel, SiteModel)
            .join(SiteModel, SiteModel.id == VehicleProviderConnectionModel.site_id)
            .where(
                VehicleProviderConnectionModel.provider == provider,
                VehicleProviderConnectionModel.enabled.is_(True),
            )
        )
        return list(result.all())

    def to_record(self, row: VehicleProviderConnectionModel) -> VehicleConnectionRecord:
        return VehicleConnectionRecord(
            id=row.id,
            site_id=row.site_id,
            provider=row.provider,
            enabled=row.enabled,
            region=row.region,
            username=row.username,
            password_configured=bool(row.encrypted_password),
            device_guid=row.device_guid,
            session_id=row.session_id,
            connection_state=row.connection_state,
            commands_enabled=row.commands_enabled,
            token_expires_at=row.token_expires_at,
            last_error=row.last_error,
            last_error_at=row.last_error_at,
            backoff_until=row.backoff_until,
            blocked_since=row.blocked_since,
            reconnect_count=row.reconnect_count,
            http_429_count=row.http_429_count,
            decode_failure_count=row.decode_failure_count,
        )

    async def update_config(
        self,
        row: VehicleProviderConnectionModel,
        *,
        enabled: bool | None = None,
        region: str | None = None,
        username: str | None = None,
        password: str | None = None,
        commands_enabled: bool | None = None,
    ) -> VehicleProviderConnectionModel:
        if enabled is not None:
            row.enabled = enabled
        if region is not None:
            row.region = region
        if username is not None:
            row.username = username
        if password:
            row.encrypted_password = self._secrets.encrypt(password)
        if commands_enabled is not None:
            row.commands_enabled = commands_enabled
        await self._session.flush()
        return row

    def decrypt_password(self, row: VehicleProviderConnectionModel) -> str:
        if not row.encrypted_password:
            return ""
        return self._secrets.decrypt(row.encrypted_password)

    def load_token_bundle(self, row: VehicleProviderConnectionModel) -> MercedesTokenBundle | None:
        if not row.encrypted_access_token or not row.encrypted_refresh_token:
            return None
        expires_at = int(row.token_expires_at.timestamp()) if row.token_expires_at else 0
        session_id = (row.session_id or "").strip() or str(uuid.uuid4()).upper()
        return MercedesTokenBundle(
            access_token=self._secrets.decrypt(row.encrypted_access_token),
            refresh_token=self._secrets.decrypt(row.encrypted_refresh_token),
            expires_at=expires_at,
            device_guid=row.device_guid or "",
            session_id=session_id,
        )

    async def persist_token_bundle(self, row: VehicleProviderConnectionModel, bundle: MercedesTokenBundle) -> None:
        row.encrypted_access_token = self._secrets.encrypt(bundle.access_token)
        row.encrypted_refresh_token = self._secrets.encrypt(bundle.refresh_token)
        row.token_expires_at = datetime.fromtimestamp(bundle.expires_at, tz=UTC)
        row.device_guid = bundle.device_guid
        row.session_id = bundle.session_id
        await self._session.flush()

    async def update_runtime_status(
        self,
        row: VehicleProviderConnectionModel,
        *,
        connection_state: str | None = None,
        last_error: str | None = None,
        backoff_until: datetime | None = None,
        blocked_since: datetime | None = None,
        reconnect_count: int | None = None,
        http_429_count: int | None = None,
        decode_failure_count: int | None = None,
    ) -> None:
        if connection_state is not None:
            row.connection_state = connection_state
        if last_error is not None:
            row.last_error = last_error[:512]
            row.last_error_at = datetime.now(UTC) if last_error else None
        if backoff_until is not None:
            row.backoff_until = backoff_until
        if blocked_since is not None:
            row.blocked_since = blocked_since
        if reconnect_count is not None:
            row.reconnect_count = reconnect_count
        if http_429_count is not None:
            row.http_429_count = http_429_count
        if decode_failure_count is not None:
            row.decode_failure_count = decode_failure_count
        await self._session.flush()


class VehicleRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool = False) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def list_for_site(self, site_id: int) -> list[VehicleRecord]:
        result = await self._session.execute(
            select(VehicleModel).where(VehicleModel.site_id == site_id, VehicleModel.enabled.is_(True))
        )
        return [self._to_record(row) for row in result.scalars().all()]

    async def get(self, vehicle_id: int) -> VehicleModel | None:
        result = await self._session.execute(select(VehicleModel).where(VehicleModel.id == vehicle_id))
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self,
        *,
        site_id: int,
        provider: str,
        external_id: str,
    ) -> VehicleModel | None:
        result = await self._session.execute(
            select(VehicleModel).where(
                VehicleModel.site_id == site_id,
                VehicleModel.provider == provider,
                VehicleModel.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_enabled(self, vehicle_id: int, *, enabled: bool) -> VehicleModel | None:
        vehicle = await self.get(vehicle_id)
        if vehicle is None:
            return None
        vehicle.enabled = enabled
        if not enabled:
            vehicle.charger_id = None
        await self._session.flush()
        return vehicle

    async def upsert_vehicle(
        self,
        *,
        site_id: int,
        provider: str,
        external_id: str,
        vin: str | None,
        manufacturer: str,
        model: str,
        display_name: str,
    ) -> VehicleModel:
        result = await self._session.execute(
            select(VehicleModel).where(
                VehicleModel.site_id == site_id,
                VehicleModel.provider == provider,
                VehicleModel.external_id == external_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.vin = vin
            existing.manufacturer = manufacturer
            existing.model = model
            if display_name:
                existing.display_name = display_name
            await self._session.flush()
            return existing
        row = VehicleModel(
            site_id=site_id,
            provider=provider,
            external_id=external_id,
            vin=vin,
            manufacturer=manufacturer,
            model=model,
            display_name=display_name or model,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def upsert_capabilities(self, vehicle_id: int, capabilities: VehicleCapabilities) -> None:
        mapping = {
            "can_read_soc": capabilities.can_read_soc,
            "can_read_range": capabilities.can_read_range,
            "can_read_charging_state": capabilities.can_read_charging_state,
            "can_read_charging_power": capabilities.can_read_charging_power,
            "can_read_target_soc": capabilities.can_read_target_soc,
            "can_read_departure_time": capabilities.can_read_departure_time,
            "can_set_target_soc": capabilities.can_set_target_soc,
            "can_start_charging": capabilities.can_start_charging,
            "can_stop_charging": capabilities.can_stop_charging,
        }
        now = datetime.now(UTC)
        for capability, available in mapping.items():
            values = {
                "vehicle_id": vehicle_id,
                "capability": capability,
                "available": available,
                "source": "discovery",
                "updated_at": now,
            }
            insert = sqlite_insert if self._is_sqlite else pg_insert
            stmt = insert(VehicleCapabilityModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["vehicle_id", "capability"],
                set_={"available": available, "updated_at": now, "source": "discovery"},
            )
            await self._session.execute(stmt)

    async def get_latest_state(self, vehicle_id: int) -> VehicleStateLatestModel | None:
        result = await self._session.execute(
            select(VehicleStateLatestModel).where(VehicleStateLatestModel.vehicle_id == vehicle_id)
        )
        return result.scalar_one_or_none()

    async def persist_state(self, vehicle_id: int, state: VehicleState) -> None:
        now = datetime.now(UTC)
        latest = await self.get_latest_state(vehicle_id)
        values = {
            "state_of_charge_percent": state.state_of_charge_percent,
            "target_soc_percent": state.target_soc_percent,
            "electric_range_km": state.electric_range_km,
            "is_plugged_in": state.is_plugged_in,
            "is_charging": state.is_charging,
            "charging_power_kw": state.charging_power_kw,
            "charging_power_limit_kw": state.charging_power_limit_kw,
            "estimated_charge_complete_at": state.estimated_charge_complete_at,
            "departure_time": state.departure_time,
            "connection_state": state.connection_state.value,
            "data_quality": state.data_quality.value,
            "last_vehicle_update": state.last_vehicle_update,
            "last_provider_update": state.last_provider_update,
            "updated_at": now,
        }
        if latest is None:
            self._session.add(VehicleStateLatestModel(vehicle_id=vehicle_id, **values))
        else:
            for key, value in values.items():
                setattr(latest, key, value)
        should_history = self._should_write_history(latest, values)
        if should_history:
            self._session.add(
                VehicleStateHistoryModel(
                    vehicle_id=vehicle_id,
                    recorded_at=now,
                    state_of_charge_percent=values["state_of_charge_percent"],
                    target_soc_percent=values["target_soc_percent"],
                    electric_range_km=values["electric_range_km"],
                    is_plugged_in=values["is_plugged_in"],
                    is_charging=values["is_charging"],
                    charging_power_kw=values["charging_power_kw"],
                    connection_state=values["connection_state"],
                    data_quality=values["data_quality"],
                )
            )
        await self._session.flush()

    def _should_write_history(self, previous: VehicleStateLatestModel | None, values: dict) -> bool:
        if previous is None:
            return True
        changed_fields = (
            "state_of_charge_percent",
            "target_soc_percent",
            "electric_range_km",
            "is_plugged_in",
            "is_charging",
            "charging_power_kw",
            "connection_state",
            "data_quality",
        )
        for field in changed_fields:
            if getattr(previous, field) != values[field]:
                return True
        if previous.updated_at and datetime.now(UTC) - previous.updated_at >= HISTORY_MIN_INTERVAL:
            return True
        return False

    def _to_record(self, row: VehicleModel) -> VehicleRecord:
        return VehicleRecord(
            id=row.id,
            site_id=row.site_id,
            provider=row.provider,
            external_id=row.external_id,
            vin=row.vin,
            manufacturer=row.manufacturer,
            model=row.model,
            display_name=row.display_name,
            enabled=row.enabled,
            charger_id=row.charger_id,
        )
