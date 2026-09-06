from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class SpaStatusResponse(BaseModel):
    consumer_id: int
    site_slug: str
    online: bool
    water_temperature_c: float | None = None
    set_temperature_c: float | None = None
    heater_active: bool = False
    pump_label: str = "Pump: Av"
    filter_status: str | None = None
    filter_cycle_active: bool = False
    errors: list[str] = Field(default_factory=list)
    current_power_w: float | None = None
    power_breakdown: dict[str, float] = Field(default_factory=dict)
    site_house_consumption_w: float | None = None
    last_updated: datetime | None = None
    data_source: str = "ARCTIC_SPA_REST"
    data_quality: str = "MISSING"
    power_note_sv: str = ""
    integration_enabled: bool = False


class SpaEnergyPeriodResponse(BaseModel):
    period: str
    energy_kwh: float = 0.0
    actual_cost_sek: float = 0.0
    reference_cost_sek: float | None = None
    savings_sek: float | None = None
    savings_pct: float | None = None
    own_energy_pct: float | None = None
    solar_direct_kwh: float = 0.0
    solar_battery_kwh: float = 0.0
    grid_battery_kwh: float = 0.0
    grid_direct_kwh: float = 0.0
    unknown_kwh: float = 0.0
    solar_kwh: float = 0.0
    battery_kwh: float = 0.0
    grid_kwh: float = 0.0
    grid_cost_sek: float = 0.0
    solar_value_sek: float = 0.0
    battery_value_sek: float = 0.0
    max_power_w: float | None = None
    avg_power_w: float | None = None
    heater_runtime_hours: float = 0.0
    pump_runtime_hours: float = 0.0
    avg_cost_sek_kwh: float | None = None
    has_data: bool = False


class SpaEnergyBreakdownRow(BaseModel):
    period_start: datetime
    period_label: str
    energy_kwh: float = 0.0
    solar_kwh: float = 0.0
    battery_kwh: float = 0.0
    grid_kwh: float = 0.0
    grid_cost_sek: float = 0.0
    solar_value_sek: float = 0.0
    battery_value_sek: float = 0.0
    savings_sek: float | None = None


class SpaEnergyBreakdownResponse(BaseModel):
    period: str
    granularity: str
    rows: list[SpaEnergyBreakdownRow] = Field(default_factory=list)
    total: SpaEnergyPeriodResponse


class SpaHistoryPoint(BaseModel):
    timestamp: datetime
    period_label: str | None = None
    power_w: float | None = None
    energy_kwh: float | None = None
    cost_sek: float | None = None
    solar_kwh: float | None = None
    battery_kwh: float | None = None
    grid_kwh: float | None = None
    grid_cost_sek: float | None = None
    solar_value_sek: float | None = None
    battery_value_sek: float | None = None
    temperature_c: float | None = None
    price_sek_kwh: float | None = None


class SpaHistoryResponse(BaseModel):
    period: str
    points: list[SpaHistoryPoint] = Field(default_factory=list)


class SpaHealthResponse(BaseModel):
    consumer_id: int
    health_status: str
    api_status: str
    spa_status: str
    polling_status: str
    database_status: str
    last_success_at: datetime | None = None
    last_sample_at: datetime | None = None
    samples_last_24h: int = 0
    samples_with_power_24h: int = 0
    sample_energy_kwh_24h: float = 0.0
    intervals_last_24h: int = 0
    data_quality: str = "MISSING"
    measured_pct: float | None = None
    calculated_pct: float | None = None
    estimated_pct: float | None = None
    missing_pct: float | None = None
    last_error: str | None = None
    actuator_state: str | None = None
    integration_degraded: bool = False
    integration_degraded_message_sv: str = ""


class SpaConfigUpdateRequest(BaseModel):
    integration_enabled: bool | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    external_spa_id: str | None = None
    poll_interval_seconds: int | None = Field(default=None, ge=15, le=600)
    energy_collection_enabled: bool | None = None
    cost_calculation_enabled: bool | None = None


class SpaConfigResponse(BaseModel):
    consumer_id: int
    integration_enabled: bool
    api_base_url: str
    masked_api_key: str
    external_spa_id: str
    poll_interval_seconds: int
    energy_collection_enabled: bool
    cost_calculation_enabled: bool
    timezone: str


class SpaConnectionTestResponse(BaseModel):
    success: bool
    spa_found: bool
    spa_online: bool
    message: str
    last_update: datetime | None = None
    masked_api_key: str = ""


class SpaReadinessResponse(BaseModel):
    enabled: bool
    configured_sites: int = 0
    online_sites: int = 0
    error_sites: int = 0


class SpaControlConfigUpdateRequest(BaseModel):
    smart_control_enabled: bool | None = None
    strategy: str | None = None
    dry_run: bool | None = None
    shadow_mode: bool | None = None
    min_cleaning_hours_per_day: float | None = Field(default=None, ge=0.5, le=24.0)
    allowed_window_start: str | None = None
    allowed_window_end: str | None = None
    prefer_solar: bool | None = None
    allow_battery: bool | None = None
    min_battery_soc_pct: float | None = Field(default=None, ge=10.0, le=90.0)
    min_run_minutes: int | None = Field(default=None, ge=15, le=240)
    min_stop_minutes: int | None = Field(default=None, ge=10, le=240)
    max_starts_per_day: int | None = Field(default=None, ge=1, le=8)
    filter_cycles_per_day: int | None = Field(default=None, ge=1, le=8)
    filter_duration_minutes: int | None = Field(default=None, ge=30, le=240)
    minimum_cycle_separation_minutes: int | None = Field(default=None, ge=10, le=240)
    filter_optimization_enabled: bool | None = None
    load_priority: int | None = Field(default=None, ge=0, le=100)
    smart_preheat_enabled: bool | None = None
    normal_temperature_c: float | None = Field(default=None, ge=30.0, le=42.0)
    max_preheat_temperature_c: float | None = Field(default=None, ge=30.0, le=42.0)
    min_comfort_temperature_c: float | None = Field(default=None, ge=30.0, le=42.0)
    fixed_schedule_start: str | None = None
    fixed_schedule_end: str | None = None


class SpaControlConfigResponse(BaseModel):
    consumer_id: int
    smart_control_enabled: bool
    strategy: str
    dry_run: bool
    shadow_mode: bool
    shadow_mode_until: datetime | None = None
    min_cleaning_hours_per_day: float
    allowed_window_start: str
    allowed_window_end: str
    prefer_solar: bool
    allow_battery: bool
    min_battery_soc_pct: float
    min_run_minutes: int
    min_stop_minutes: int
    max_starts_per_day: int
    filter_cycles_per_day: int
    filter_duration_minutes: int
    minimum_cycle_separation_minutes: int
    filter_optimization_enabled: bool
    safety_floor_frequency_per_day: float
    safety_floor_duration_hours: float
    smart_preheat_enabled: bool
    normal_temperature_c: float
    max_preheat_temperature_c: float
    min_comfort_temperature_c: float
    load_priority: int
    fixed_schedule_start: str | None = None
    fixed_schedule_end: str | None = None


class SpaPlanBlockResponse(BaseModel):
    timestamp: datetime
    score: float
    solar_forecast_w: float
    house_load_forecast_w: float
    available_surplus_w: float
    marginal_cost_sek_kwh: float
    expected_energy_source: str
    price_estimated: bool


class SpaCleaningWindowResponse(BaseModel):
    start: datetime
    end: datetime
    duration_hours: float
    energy_source_label_sv: str
    solar_share_pct: float | None = None


class SpaPlanResponse(BaseModel):
    enabled: bool
    consumer_id: int | None = None
    load_id: str = "spa_cleaning"
    strategy: str | None = None
    next_cleaning_start: datetime | None = None
    next_cleaning_end: datetime | None = None
    duration_hours: float | None = None
    planned_energy_source: str | None = None
    estimated_energy_kwh: float | None = None
    estimated_cost_sek: float | None = None
    baseline_cost_sek: float | None = None
    savings_sek: float | None = None
    explanation_sv: str = ""
    reason: str | None = None
    reason_sv: str | None = None
    fallback_from_solar_only: bool = False
    dry_run: bool = True
    data_quality: str = "ESTIMATED"
    blocks: list[SpaPlanBlockResponse] = Field(default_factory=list)
    daily_windows: list[SpaCleaningWindowResponse] = Field(default_factory=list)
    daily_target_hours: float | None = None
    daily_completed_hours: float | None = None
    daily_progress_pct: float | None = None
    planned_starts: int | None = None
    max_starts_per_day: int | None = None
    starts_used_today: int | None = None
    config_summary_sv: str | None = None
    config_validation_warning_sv: str | None = None
    filter_control_source_sv: str | None = None
    timing_optimization_source_sv: str | None = None
    filter_policy_summary_sv: str | None = None
    optimization_hint_sv: str | None = None
    cycles_planned: int | None = None
    cycles_completed_today: int | None = None
    hours_planned: float | None = None
    next_cycle_starts_in_minutes: int | None = None
    remaining_cycles_today: int | None = None


class SpaTimelineEntry(BaseModel):
    timestamp: datetime
    hour_label: str
    action: str
    action_sv: str
    load_id: str | None = None
    energy_source: str | None = None


class SpaTimelineResponse(BaseModel):
    entries: list[SpaTimelineEntry] = Field(default_factory=list)


class SpaEnergyEventResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    start_time: datetime | None = None
    stop_time: datetime | None = None
    runtime_seconds: float | None = None
    estimated_kwh: float | None = None
    actual_kwh: float | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None
    solar_share: float | None = None
    battery_share: float | None = None
    grid_share: float | None = None
    reason: str
    reason_sv: str
    strategy: str
    decision_score: float | None = None
    manual_override: bool = False
    dry_run: bool = True
    data_quality: str = "ESTIMATED"


class SpaEventsResponse(BaseModel):
    events: list[SpaEnergyEventResponse] = Field(default_factory=list)
    total: int = 0


class SpaEconomicsResponse(BaseModel):
    period: str
    energy_kwh: float = 0.0
    cost_sek: float = 0.0
    baseline_cost_sek: float | None = None
    savings_sek: float | None = None
    solar_share_pct: float | None = None
    battery_share_pct: float | None = None
    grid_share_pct: float | None = None
    data_quality: str = "ESTIMATED"


class SpaShadowDayResponse(BaseModel):
    date_label: str
    actual_cost_sek: float
    optimized_cost_sek: float
    potential_saving_sek: float


class SpaShadowResponse(BaseModel):
    shadow_mode_active: bool
    total_actual_cost_sek: float
    total_optimized_cost_sek: float
    total_potential_saving_sek: float
    days: list[SpaShadowDayResponse] = Field(default_factory=list)
    integration_degraded: bool = False
    integration_degraded_message_sv: str = ""


class SpaRunCleaningResponse(BaseModel):
    success: bool
    message: str
    dry_run: bool = True
