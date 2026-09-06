from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class ReadingResponse(BaseModel):
    recorded_at: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float


class SiteResponse(BaseModel):
    slug: str
    name: str
    timezone: str
    external_system_id: str | None = None
    fallback_purchase_price_sek_kwh: float
    export_compensation_sek_kwh: float
    main_fuse_a: float | None = None
    safety_margin_a: float = 2.0
    sell_contract_start_date: date | None = None
    latest_reading: ReadingResponse | None = None


class SiteCreateRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    timezone: str = Field(min_length=1, max_length=64)
    external_system_id: str | None = None
    fallback_purchase_price_sek_kwh: float = Field(default=2.0, ge=0, le=20)
    export_compensation_sek_kwh: float = Field(default=0.8, ge=0, le=20)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        import re

        slug = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError("Slug får bara innehålla a-z, 0-9 och bindestreck.")
        return slug

    @field_validator("name", "timezone", mode="before")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return str(value).strip()


class SiteUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    external_system_id: str | None = None
    fallback_purchase_price_sek_kwh: float | None = Field(default=None, ge=0, le=20)
    export_compensation_sek_kwh: float | None = Field(default=None, ge=0, le=20)
    main_fuse_a: float | None = Field(default=None, gt=0, le=200)
    safety_margin_a: float | None = Field(default=None, ge=0, le=50)
    sell_contract_start_date: date | None = None


class SiteEnergyConfigResponse(BaseModel):
    site_slug: str
    load_includes_ev_charger: bool | None = None
    inverter_display_name: str = "Sungrow Hybrid Inverter SH10"
    physical_ev_charger_label: str = "Charge Amps Halo"
    ev_vehicle_label: str = "Mercedes EQE 500"


class SiteEnergyConfigUpdateRequest(BaseModel):
    load_includes_ev_charger: bool | None = None
    clear_load_includes_ev_charger: bool = False
    inverter_display_name: str | None = Field(default=None, min_length=1, max_length=128)
    physical_ev_charger_label: str | None = Field(default=None, min_length=1, max_length=128)
    ev_vehicle_label: str | None = Field(default=None, min_length=1, max_length=128)
