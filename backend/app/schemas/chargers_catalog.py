from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class ChargerManufacturerResponse(BaseModel):
    id: str
    name: str
    model_count: int


class ChargerCatalogModelResponse(BaseModel):
    id: str
    manufacturer_id: str
    name: str
    status: str
    supported_protocols: list[str]
    integration_methods: list[str]
    documentation_url: str | None = None
    capabilities: dict[str, bool]


class ChargerIntegrationMethodResponse(BaseModel):
    id: str
    label: str
    protocol: str
    connection_type: str
    recommended: bool
    priority: int
    implementation_status: str
    cloud_dependent: bool
    documentation_url: str | None = None
    credential_fields: list[dict[str, object]]
    connection_fields: list[dict[str, object]]


class ChargerModelDetailResponse(BaseModel):
    model: ChargerCatalogModelResponse
    integration_methods: list[ChargerIntegrationMethodResponse]


class ChargerConnectionTestResponse(BaseModel):
    success: bool
    status: str
    message: str
    model_mismatch: bool = False
    detected_device: dict[str, str | None] | None = None
    capabilities: dict[str, object] | None = None
