from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

from app.schemas.ev import EvEnergySourcesResponse


class VehicleCapabilitiesResponse(BaseModel):
    can_read_soc: bool | None = None
    can_read_range: bool | None = None
    can_read_charging_state: bool | None = None
    can_read_charging_power: bool | None = None
    can_read_target_soc: bool | None = None
    can_read_departure_time: bool | None = None
    can_set_target_soc: bool | None = None
    can_start_charging: bool | None = None
    can_stop_charging: bool | None = None

    @classmethod
    def from_rows(cls, rows: list) -> VehicleCapabilitiesResponse:
        mapping = {row.capability: row.available for row in rows}

        def _value(key: str) -> bool | None:
            return mapping[key] if key in mapping else None

        return cls(
            can_read_soc=_value("can_read_soc"),
            can_read_range=_value("can_read_range"),
            can_read_charging_state=_value("can_read_charging_state"),
            can_read_charging_power=_value("can_read_charging_power"),
            can_read_target_soc=_value("can_read_target_soc"),
            can_read_departure_time=_value("can_read_departure_time"),
            can_set_target_soc=_value("can_set_target_soc"),
            can_start_charging=_value("can_start_charging"),
            can_stop_charging=_value("can_stop_charging"),
        )


class VehicleHaloCorrelationResponse(BaseModel):
    charger_id: int | None = None
    confidence: float = 0.0
    status: str = "UNAVAILABLE"
    plugged_agreement: bool | None = None
    charging_agreement: bool | None = None
    power_delta_kw: float | None = None
    vehicle_power_kw: float | None = None
    halo_power_kw: float | None = None
    notes: str = ""
    updated_at: datetime | None = None


class VehicleValueResponse(BaseModel):
    value: float | bool | str | None = None
    source_timestamp: datetime | None = None
    received_timestamp: datetime | None = None
    age_seconds: float | None = None
    quality: str


class VehicleListItemResponse(BaseModel):
    id: int
    site_id: int
    provider: str
    display_name: str
    manufacturer: str
    model: str
    masked_vin: str | None = None
    enabled: bool
    connection_state: str
    data_quality: str
    freshness_label: str
    state_of_charge_percent: float | None = None
    target_soc_percent: float | None = None
    electric_range_km: float | None = None
    is_plugged_in: bool | None = None
    is_charging: bool | None = None
    charging_power_kw: float | None = None
    last_vehicle_update: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    charger_operator: str | None = None
    capabilities: VehicleCapabilitiesResponse
    halo_correlation: VehicleHaloCorrelationResponse | None = None
    state_of_charge: VehicleValueResponse | None = None
    charging_power: VehicleValueResponse | None = None
    electric_range: VehicleValueResponse | None = None


class VehicleListResponse(BaseModel):
    site_slug: str
    vehicles: list[VehicleListItemResponse] = Field(default_factory=list)


class VehicleSyncResponse(VehicleListResponse):
    synced_at: datetime
    vehicles_updated: int = 0


class VehicleDetailResponse(VehicleListItemResponse):
    charger_id: int | None = None


class VehicleUpdateRequest(BaseModel):
    enabled: bool | None = None
    display_name: str | None = None


class VehicleIntegrationStatusResponse(BaseModel):
    site_slug: str
    provider: str
    enabled: bool
    region: str
    username: str
    password_configured: bool
    connection_state: str
    commands_enabled: bool
    token_expires_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    backoff_until: datetime | None = None
    blocked_since: datetime | None = None
    reconnect_count: int = 0
    http_429_count: int = 0
    decode_failure_count: int = 0
    health: str = "HEALTHY"
    health_status: str = "unavailable"


class VehicleIntegrationConfigResponse(BaseModel):
    site_slug: str
    provider: str
    enabled: bool
    region: str
    username: str
    password_configured: bool
    commands_enabled: bool


class VehicleIntegrationConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    region: str | None = None
    username: str | None = None
    password: str | None = None
    commands_enabled: bool | None = None


class VehicleIntegrationLoginResponse(BaseModel):
    success: bool
    message: str


class VehicleAttributeObservationResponse(BaseModel):
    attribute_name: str
    source: str
    value_type: str
    masked_sample: str
    first_seen_at: datetime
    last_seen_at: datetime
    sample_count: int


class VehicleRawAttributesResponse(BaseModel):
    site_slug: str
    vehicle_id: int | None = None
    observations: list[VehicleAttributeObservationResponse] = Field(default_factory=list)


class VehicleApiEventResponse(BaseModel):
    endpoint: str
    method: str
    http_status: int | None = None
    duration_ms: int
    error_code: str | None = None
    retry_count: int = 0
    recorded_at: datetime


class VehicleIntegrationEventResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    message: str
    details_json: str = "{}"
    vehicle_id: int | None = None
    recorded_at: datetime


class VehicleIntegrationDiagnosticsResponse(BaseModel):
    site_slug: str
    health_status: str
    unified_health_status: str
    connection_state: str
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_vehicle_update: datetime | None = None
    last_token_refresh_at: datetime | None = None
    consecutive_failures: int = 0
    last_error_code: str | None = None
    last_latency_ms: int | None = None
    current_polling_interval_seconds: int | None = None
    vehicle_data_age_seconds: float | None = None
    api_data_age_seconds: float | None = None
    soc_updated_at: datetime | None = None
    soc_age_seconds: float | None = None
    recent_events: list[VehicleApiEventResponse] = Field(default_factory=list)
    integration_events: list[VehicleIntegrationEventResponse] = Field(default_factory=list)


class VehicleIntegrationActionResponse(BaseModel):
    success: bool
    message: str


class VehicleSetTargetSocRequest(BaseModel):
    target_soc_percent: int = Field(ge=30, le=100)


class VehicleCommandResponse(BaseModel):
    success: bool
    message: str
    vehicle_id: int
    command: str


class VehicleReadinessResponse(BaseModel):
    enabled_sites: int = 0
    connected_sites: int = 0
    degraded_sites: int = 0


class StationCandidateResponse(BaseModel):
    score: int
    label: str
    provider_station_id: str | None = None


class VehicleChargeSessionResponse(BaseModel):
    id: int
    vehicle_id: int
    charger_id: int | None = None
    connected_at: datetime
    disconnected_at: datetime | None = None
    charging_started_at: datetime | None = None
    charging_stopped_at: datetime | None = None
    start_soc: float | None = None
    end_soc: float | None = None
    target_soc: float | None = None
    status: str
    halo_energy_kwh: float | None = None
    estimated_battery_energy_delta_kwh: float | None = None
    energy_sources: EvEnergySourcesResponse
    actual_cost_sek: float | None = None
    reference_cost_sek: float | None = None
    savings_sek: float | None = None
    renewable_share_pct: float | None = None
    grid_share_pct: float | None = None
    identification_confidence: float | None = None
    energy_quality: str | None = None
    cost_quality: str | None = None
    attribution_quality: str | None = None
    location_name: str | None = None
    charger_operator: str | None = None
    charging_type: str | None = None
    home_charging: bool | None = None
    energy_source: str | None = None
    estimated_energy_kwh: float | None = None
    charging_cost_sek: float | None = None
    cost_source: str | None = None
    price_model: str | None = None
    price_value_sek_kwh: float | None = None
    detection_confidence: str | None = None
    identification_method: str | None = None
    vehicle_data_quality: str | None = None
    charging_power_avg_kw: float | None = None
    charging_power_max_kw: float | None = None
    connector_type: str | None = None
    station_name: str | None = None
    station_provider: str | None = None
    station_provider_id: str | None = None
    distance_from_vehicle_m: float | None = None
    station_confidence: int | None = None
    station_resolution_status: str | None = None
    station_candidates: list[StationCandidateResponse] = Field(default_factory=list)


class VehicleChargeSessionPatchRequest(BaseModel):
    location_name: str | None = None
    charger_operator: str | None = None
    charging_type: str | None = None
    charging_cost_sek: float | None = None
    home_charging: bool | None = None
    station_provider_id: str | None = None
    station_name: str | None = None
    station_provider: str | None = None


class VehicleChargingStatsResponse(BaseModel):
    site_slug: str
    vehicle_id: int | None = None
    period: str
    total_energy_kwh: float
    home_energy_kwh: float
    away_energy_kwh: float
    ac_energy_kwh: float
    dc_energy_kwh: float
    free_energy_kwh: float
    paid_energy_kwh: float
    avg_price_sek_kwh: float | None = None
    total_cost_sek: float
    savings_vs_public_sek: float | None = None
    solar_share_pct: float | None = None
    grid_share_pct: float | None = None
    session_count: int


class VehicleChargeSessionListResponse(BaseModel):
    site_slug: str
    vehicle_id: int
    sessions: list[VehicleChargeSessionResponse] = Field(default_factory=list)
