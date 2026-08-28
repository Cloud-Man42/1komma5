from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.heartbeat_connection import CLOUD_PORT, HeartbeatConnectionType
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


class EvChargerResponse(BaseModel):
    id: int
    site_slug: str
    name: str
    manufacturer: str
    model: str
    control_source: str = "chargeamp"
    heartbeat_ev_id: str | None = None
    heartbeat_charger_id: str | None = None
    chargeamp_charger_id: str | None = None
    bridge_enabled: bool = False
    max_current_a: float = 16.0
    min_current_a: float = 6.0
    phases: int = 3
    nominal_voltage_v: float = 230.0
    max_power_w: float | None = None
    max_grid_import_w: float | None = None
    update_interval_seconds: int = 30
    min_change_interval_seconds: int = 60
    current_hysteresis_a: float = 1.0
    stale_timeout_seconds: int = 120
    chargeamps_api_key_configured: bool = False
    last_applied_current_a: float | None = None
    last_bridge_run_at: datetime | None = None
    last_heartbeat_data_at: datetime | None = None
    override_until: datetime | None = None
    override_active: bool = False
    charging_mode: str | None = None
    target_soc_pct: float | None = None
    manual_soc_pct: float | None = None
    departure_time: str | None = None
    power_w: float | None = None
    available_modes: list[str] = Field(default_factory=list)
    deadline_at: datetime | None = None
    solar_start_threshold_w: float = 1500.0
    solar_stop_threshold_w: float = 800.0
    solar_start_delay_seconds: int = 30
    solar_stop_delay_seconds: int = 60
    last_charging_action: str | None = None
    last_charging_reason: str | None = None
    last_charger_error_code: str | None = None
    last_halo_connected: bool | None = None
    last_vehicle_connected: bool | None = None
    smart_charging_state: str | None = None
    last_requested_current_a: float | None = None
    last_configured_current_a: float | None = None
    last_actual_charging_current_a: float | None = None
    last_actual_power_w: float | None = None
    externally_limited: bool | None = None
    start_delay_seconds: int = 120
    stop_delay_seconds: int = 300
    minimum_run_time_seconds: int = 300
    minimum_off_time_seconds: int = 300
    temporary_grid_import_allowance_w: float = 800.0
    temporary_grid_import_seconds: int = 180
    grid_deadband_w: float = 300.0
    minimum_current_change_interval_seconds: int = 30
    max_current_increase_per_step_a: float = 1.0
    max_current_decrease_per_step_a: float = 2.0
    max_automatic_starts_per_hour: int = 4
    virtual_evse_enabled: bool = False
    semp_device_id: str | None = None
    manufacturer_id: str | None = None
    model_id: str | None = None
    integration_method: str | None = None
    external_charger_id: str | None = None
    connection_settings: dict[str, object] = Field(default_factory=dict)
    connection_status: str = "NOT_CONFIGURED"
    last_connection_at: datetime | None = None
    last_connection_test_at: datetime | None = None


class EvChargerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    manufacturer: str = "ChargeAmps"
    model: str = "Halo"
    control_source: str = "chargeamp"
    heartbeat_ev_id: str | None = None
    heartbeat_charger_id: str | None = None
    chargeamp_charger_id: str | None = None
    bridge_enabled: bool = False
    max_current_a: float = Field(default=16.0, gt=0, le=32)
    min_current_a: float = Field(default=6.0, ge=0, le=32)
    phases: int = Field(default=3, ge=1, le=3)
    nominal_voltage_v: float = Field(default=230.0, gt=0)
    max_power_w: float | None = Field(default=None, ge=0)
    max_grid_import_w: float | None = Field(default=None, ge=0)
    update_interval_seconds: int = Field(default=30, ge=10, le=600)
    min_change_interval_seconds: int = Field(default=60, ge=10, le=600)
    current_hysteresis_a: float = Field(default=1.0, ge=0)
    stale_timeout_seconds: int = Field(default=120, ge=30, le=3600)
    chargeamps_api_key: str | None = None
    charging_mode: str | None = None
    departure_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    target_soc_pct: float | None = Field(default=None, ge=0, le=100)
    deadline_at: datetime | None = None
    solar_start_threshold_w: float | None = Field(default=None, ge=0)
    solar_stop_threshold_w: float | None = Field(default=None, ge=0)
    solar_start_delay_seconds: int | None = Field(default=None, ge=0, le=600)
    solar_stop_delay_seconds: int | None = Field(default=None, ge=0, le=600)
    start_delay_seconds: int | None = Field(default=None, ge=0, le=3600)
    stop_delay_seconds: int | None = Field(default=None, ge=0, le=3600)
    minimum_run_time_seconds: int | None = Field(default=None, ge=0, le=3600)
    minimum_off_time_seconds: int | None = Field(default=None, ge=0, le=3600)
    temporary_grid_import_allowance_w: float | None = Field(default=None, ge=0)
    temporary_grid_import_seconds: int | None = Field(default=None, ge=0, le=3600)
    grid_deadband_w: float | None = Field(default=None, ge=0)
    minimum_current_change_interval_seconds: int | None = Field(default=None, ge=0, le=600)
    max_current_increase_per_step_a: float | None = Field(default=None, ge=0, le=32)
    max_current_decrease_per_step_a: float | None = Field(default=None, ge=0, le=32)
    max_automatic_starts_per_hour: int | None = Field(default=None, ge=1, le=20)
    virtual_evse_enabled: bool | None = None
    manufacturer_id: str | None = None
    model_id: str | None = None
    integration_method: str | None = None
    external_charger_id: str | None = None
    connection_settings: dict[str, object] | None = None


class EvChargerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    manufacturer: str | None = None
    model: str | None = None
    heartbeat_ev_id: str | None = None
    heartbeat_charger_id: str | None = None
    chargeamp_charger_id: str | None = None
    bridge_enabled: bool | None = None
    max_current_a: float | None = Field(default=None, gt=0, le=32)
    min_current_a: float | None = Field(default=None, ge=0, le=32)
    phases: int | None = Field(default=None, ge=1, le=3)
    nominal_voltage_v: float | None = Field(default=None, gt=0)
    max_power_w: float | None = Field(default=None, ge=0)
    max_grid_import_w: float | None = Field(default=None, ge=0)
    update_interval_seconds: int | None = Field(default=None, ge=10, le=600)
    min_change_interval_seconds: int | None = Field(default=None, ge=10, le=600)
    current_hysteresis_a: float | None = Field(default=None, ge=0)
    stale_timeout_seconds: int | None = Field(default=None, ge=30, le=3600)
    chargeamps_api_key: str | None = None
    clear_chargeamps_api_key: bool = False
    charging_mode: str | None = None
    departure_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    clear_departure_time: bool = False
    target_soc_pct: float | None = Field(default=None, ge=0, le=100)
    deadline_at: datetime | None = None
    clear_deadline_at: bool = False
    solar_start_threshold_w: float | None = Field(default=None, ge=0)
    solar_stop_threshold_w: float | None = Field(default=None, ge=0)
    solar_start_delay_seconds: int | None = Field(default=None, ge=0, le=600)
    solar_stop_delay_seconds: int | None = Field(default=None, ge=0, le=600)
    start_delay_seconds: int | None = Field(default=None, ge=0, le=3600)
    stop_delay_seconds: int | None = Field(default=None, ge=0, le=3600)
    minimum_run_time_seconds: int | None = Field(default=None, ge=0, le=3600)
    minimum_off_time_seconds: int | None = Field(default=None, ge=0, le=3600)
    temporary_grid_import_allowance_w: float | None = Field(default=None, ge=0)
    temporary_grid_import_seconds: int | None = Field(default=None, ge=0, le=3600)
    grid_deadband_w: float | None = Field(default=None, ge=0)
    minimum_current_change_interval_seconds: int | None = Field(default=None, ge=0, le=600)
    max_current_increase_per_step_a: float | None = Field(default=None, ge=0, le=32)
    max_current_decrease_per_step_a: float | None = Field(default=None, ge=0, le=32)
    max_automatic_starts_per_hour: int | None = Field(default=None, ge=1, le=20)
    virtual_evse_enabled: bool | None = None
    manufacturer_id: str | None = None
    model_id: str | None = None
    integration_method: str | None = None
    external_charger_id: str | None = None
    connection_settings: dict[str, object] | None = None


class EvChargerConnectionTestRequest(BaseModel):
    manufacturer_id: str
    model_id: str
    integration_method: str
    chargeamp_charger_id: str | None = None
    external_charger_id: str | None = None
    chargeamps_api_key: str | None = None
    connection_settings: dict[str, object] = Field(default_factory=dict)
    max_current_a: float = Field(default=16.0, gt=0, le=32)
    min_current_a: float = Field(default=6.0, ge=0, le=32)
    phases: int = Field(default=3, ge=1, le=3)
    nominal_voltage_v: float = Field(default=230.0, gt=0)


class EvBridgeStatusResponse(BaseModel):
    charger_id: int
    bridge_enabled: bool
    charging_mode: str
    active_policy: str
    ev_target_power_w: float | None = None
    requested_current_a: float | None = None
    applied_current_a: float | None = None
    previous_current_a: float | None = None
    configured_current_a: float | None = None
    actual_charging_current_a: float | None = None
    actual_power_w: float | None = None
    smart_charging_state: str | None = None
    externally_limited: bool = False
    display_status_sv: str | None = None
    fuse_headroom_a: float | None = None
    last_heartbeat_data_at: datetime | None = None
    last_bridge_run_at: datetime | None = None
    halo_connected: bool | None = None
    vehicle_connected: bool | None = None
    decision_reason: str | None = None
    discovery_hints: list[str] = Field(default_factory=list)
    stale: bool = False
    override_active: bool = False
    override_until: datetime | None = None
    last_error_code: str | None = None
    last_charging_action: str | None = None
    phase_current_l1_a: float | None = None
    phase_current_l2_a: float | None = None
    phase_current_l3_a: float | None = None
    sungrow_fresh: bool | None = None
    sungrow_telemetry_age_seconds: float | None = None
    energy_balance_status: str | None = None
    energy_balance_alignment_delta_seconds: float | None = None
    energy_balance_flags: list[str] = Field(default_factory=list)


class EnergyBalanceResponse(BaseModel):
    charger_id: int
    recorded_at: datetime | None = None
    status: str
    flags: list[str] = Field(default_factory=list)
    inverter_display_name: str = "Sungrow Hybrid Inverter SH10"
    sungrow_pv_power_w: float | None = None
    sungrow_load_power_w: float | None = None
    sungrow_grid_import_w: float | None = None
    sungrow_grid_export_w: float | None = None
    sungrow_battery_charge_w: float | None = None
    sungrow_battery_discharge_w: float | None = None
    sungrow_battery_soc_pct: float | None = None
    sungrow_fresh: bool | None = None
    sungrow_telemetry_age_seconds: float | None = None
    halo_power_w: float | None = None
    virtual_evse_reported_power_w: float | None = None
    heartbeat_observed_ev_power_w: float | None = None
    heartbeat_home_consumption_w: float | None = None
    non_ev_house_load_w: float | None = None
    non_ev_house_load_reason: str | None = None
    residual_w: float | None = None
    alignment_delta_seconds: float | None = None
    energy_flow_line: str | None = None


class EnergyBalanceHistoryResponse(BaseModel):
    items: list[EnergyBalanceResponse]
    total: int


class VirtualEvseStatusResponse(BaseModel):
    charger_id: int
    virtual_evse_enabled: bool
    semp_device_id: str | None = None
    status: str | None = None
    reported_power_w: float | None = None
    halo_power_w: float | None = None
    heartbeat_observed_ev_power_w: float | None = None
    heartbeat_detected: bool = False
    vehicle_connected: bool | None = None
    stale: bool = False
    physical_charger_label: str = "Charge Amps Halo"
    ev_vehicle_label: str = "Mercedes EQE 500"


class EnergyReasoningResponse(BaseModel):
    charger_id: int
    bridge_enabled: bool
    charging_active: bool
    charging_mode: str
    heartbeat_charging_mode: str | None = None
    ev_charge_from_grid_recommended: bool = False
    ev_target_power_w: float | None = None
    pv_power_w: float | None = None
    grid_import_w: float | None = None
    grid_export_w: float | None = None
    home_consumption_w: float | None = None
    battery_soc_pct: float | None = None
    ev_actual_power_w: float | None = None
    current_price_eur_kwh: float | None = None
    price_average_eur_kwh: float | None = None
    price_tier: str = "unknown"
    price_would_charge: bool = False
    price_reason: str = ""
    smart_charging_state: str | None = None
    decision_reason: str | None = None
    decision_reason_sv: str | None = None
    display_status_sv: str | None = None
    requested_current_a: float | None = None
    applied_current_a: float | None = None
    vehicle_connected: bool | None = None
    halo_connected: bool | None = None
    solar_plan_available: bool = False
    solar_plan_reason: str | None = None
    solar_first: bool = False
    active_optimizations: list[str] = Field(default_factory=list)
    energy_flow_line: str | None = None
    energy_balance_status: str | None = None
    reasoning_steps: list[str] = Field(default_factory=list)
    vehicle_linked: bool = False
    vehicle_display_name: str | None = None
    vehicle_soc_pct: float | None = None
    vehicle_target_soc_pct: float | None = None
    vehicle_required_energy_kwh: float | None = None
    vehicle_departure_time: str | None = None
    vehicle_energy_quality: str | None = None


class SolarChargingPlanResponse(BaseModel):
    available: bool
    expected_usable_solar_kwh: float | None = None
    planning_solar_kwh: float | None = None
    solar_first: bool = False
    quality: str | None = None
    confidence: float | None = None
    expected_solar_window_start: datetime | None = None
    expected_solar_window_end: datetime | None = None
    cheapest_grid_window: str | None = None
    explanation_sv: str | None = None
    reason_code: str | None = None


class EvChargerOverrideRequest(BaseModel):
    hours: int | None = Field(default=None)
    clear: bool = False


class EvChargingSavingsResponse(BaseModel):
    charger_id: int
    period_from: datetime
    period_to: datetime
    energy_kwh: float
    actual_cost_sek: float
    baseline_cost_sek: float
    savings_sek: float
    savings_ore: int
    savings_pct: float
    charging_intervals: int
    period_avg_price_kwh: float | None = None
    has_data: bool = False


class EvChargerControlRequest(BaseModel):
    charging_mode: str | None = None
    target_soc_pct: float | None = Field(default=None, ge=0, le=100)
    manual_soc_pct: float | None = Field(default=None, ge=0, le=100)
    departure_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    deadline_at: datetime | None = None
    clear_deadline_at: bool = False


class AggregatedReadingResponse(BaseModel):
    bucket_start: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float


class HistoryResponse(BaseModel):
    slug: str
    bucket_minutes: int
    readings: list[ReadingResponse | AggregatedReadingResponse] = Field(default_factory=list)


class PeakReadingResponse(BaseModel):
    period_start: str
    solar_production_w: float
    consumption_w: float
    battery_charge_w: float
    battery_discharge_w: float


class PeaksResponse(BaseModel):
    slug: str
    timezone: str
    period: str
    peaks: list[PeakReadingResponse] = Field(default_factory=list)


class FinancialStatResponse(BaseModel):
    period_start: str
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    exported_kwh: float
    imported_kwh: float
    solar_savings_sek: float
    battery_savings_sek: float
    export_revenue_sek: float
    grid_import_cost_sek: float
    market_priced_fraction: float


class FinancialStatsResponse(BaseModel):
    slug: str
    timezone: str
    period: str
    fallback_purchase_price_sek_kwh: float
    export_compensation_sek_kwh: float
    stats: list[FinancialStatResponse] = Field(default_factory=list)


class ForecastValuesResponse(BaseModel):
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    exported_kwh: float
    imported_kwh: float
    solar_savings_sek: float
    battery_savings_sek: float
    export_revenue_sek: float
    grid_import_cost_sek: float
    net_sek: float


class MonthlyForecastResponse(BaseModel):
    month: str
    actual: ForecastValuesResponse
    forecast: ForecastValuesResponse
    total: ForecastValuesResponse


class YearForecastResponse(BaseModel):
    slug: str
    timezone: str
    year: int
    observed_days: int
    confidence: str
    uncertainty_pct: int
    import_baseline_year: int | None = None
    import_baseline_source: str | None = None
    import_baseline_estimated: bool = False
    import_baseline_kwh: float | None = None
    fallback_purchase_price_sek_kwh: float
    export_compensation_sek_kwh: float
    actual: ForecastValuesResponse
    forecast: ForecastValuesResponse
    total: ForecastValuesResponse
    months: list[MonthlyForecastResponse]


class HistoricalEnergyMonth(BaseModel):
    month: int = Field(ge=1, le=12)
    imported_kwh: float = Field(ge=0)
    imported_cost_sek: float | None = Field(default=None, ge=0)


class HistoricalEnergyYearUpdate(BaseModel):
    source: str = Field(default="", max_length=128)
    estimated: bool = False
    months: list[HistoricalEnergyMonth] = Field(min_length=12, max_length=12)


class HistoricalEnergyYearResponse(BaseModel):
    slug: str
    year: int
    source: str
    estimated: bool
    total_imported_kwh: float
    total_imported_cost_sek: float | None
    months: list[HistoricalEnergyMonth]


class MarketPricePointResponse(BaseModel):
    timestamp: datetime
    spot_eur_kwh: float
    all_in_eur_kwh: float | None = None


class MarketPricesResponse(BaseModel):
    slug: str
    timezone: str
    resolution: str
    current_price_eur_kwh: float | None = None
    average_all_in_eur_kwh: float | None = None
    highest_all_in_eur_kwh: float | None = None
    lowest_all_in_eur_kwh: float | None = None
    points: list[MarketPricePointResponse] = Field(default_factory=list)


class SiteHeartbeatMappingResponse(BaseModel):
    slug: str
    name: str
    external_system_id: str | None = None


class HeartbeatConfigResponse(BaseModel):
    connection_type: str
    connection_type_label: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    poll_interval_seconds: int
    dashboard_refresh_seconds: int
    api_url: str | None = None
    username: str = ""
    password_configured: bool
    api_token_configured: bool
    connection_mode: str
    contacting_component: str
    implementation_status: str
    notes: list[str] = Field(default_factory=list)
    sites: list[SiteHeartbeatMappingResponse] = Field(default_factory=list)
    updated_at: datetime | None = None


class SiteHeartbeatMappingUpdate(BaseModel):
    slug: str
    external_system_id: str | None = None


class HeartbeatConfigUpdateRequest(BaseModel):
    connection_type: HeartbeatConnectionType
    host: str = ""
    port: int = Field(default=CLOUD_PORT, ge=1, le=65535)
    use_tls: bool = True
    api_path: str = "/api"
    poll_interval_seconds: int = Field(default=60, ge=5, le=3600)
    dashboard_refresh_seconds: int = Field(default=30, ge=1, le=30)
    username: str = ""
    password: str | None = None
    api_token: str | None = None
    sites: list[SiteHeartbeatMappingUpdate] = Field(default_factory=list)

    @field_validator("connection_type", mode="before")
    @classmethod
    def normalize_connection_type(cls, value: str | HeartbeatConnectionType) -> HeartbeatConnectionType:
        if isinstance(value, HeartbeatConnectionType):
            return value
        return HeartbeatConnectionType(str(value).lower())

    @field_validator("host", "username", "api_path", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str:
        return (value or "").strip()


class ChargeAmpsConfigResponse(BaseModel):
    provider: str
    effective_provider: str
    mock: bool
    api_key_configured: bool
    env_api_key_configured: bool
    charger_api_keys_configured: int = 0
    email_configured: bool
    password_configured: bool
    ready: bool
    notes: list[str] = Field(default_factory=list)


class ChargerReadinessIssueResponse(BaseModel):
    site_slug: str
    charger_id: int
    charger_name: str
    code: str
    message: str


class ChargingReadinessResponse(BaseModel):
    ready: bool
    chargeamps_ready: bool
    active_bridge_chargers: int
    issues: list[ChargerReadinessIssueResponse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvEnergySourcesResponse(BaseModel):
    solar_direct_kwh: float
    solar_battery_kwh: float
    grid_battery_kwh: float
    grid_direct_kwh: float


class EvChargingIntervalResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    charged_energy_kwh: float
    average_charging_power_w: float | None = None
    pv_production_kwh: float | None = None
    house_consumption_kwh: float | None = None
    grid_import_kwh: float | None = None
    grid_export_kwh: float | None = None
    battery_charge_kwh: float | None = None
    battery_discharge_kwh: float | None = None
    electricity_price_sek_kwh: float | None = None
    energy_sources: EvEnergySourcesResponse
    actual_cost_sek: float
    reference_cost_sek: float | None = None
    savings_sek: float | None = None
    confidence: float | None = None
    data_quality: str | None = None


class EvChargingSessionResponse(BaseModel):
    id: int
    charger_id: int
    started_at: datetime
    ended_at: datetime | None = None
    status: str
    total_energy_kwh: float | None = None
    energy_sources: EvEnergySourcesResponse
    actual_cost_sek: float | None = None
    reference_cost_sek: float | None = None
    savings_sek: float | None = None
    smart_charging_savings_sek: float | None = None
    solar_contribution_sek: float | None = None
    renewable_share_pct: float | None = None
    grid_share_pct: float | None = None
    average_cost_sek_per_kwh: float | None = None
    energy_quality: str | None = None
    cost_quality: str | None = None
    attribution_quality: str | None = None
    savings_baseline: str
    calculation_version: str
    reconciliation_delta_kwh: float | None = None
    intervals: list[EvChargingIntervalResponse] = Field(default_factory=list)


class EvChargingStatsResponse(BaseModel):
    period: str
    period_from: datetime
    period_to: datetime
    total_energy_kwh: float
    actual_cost_sek: float
    reference_cost_sek: float | None = None
    savings_sek: float | None = None
    average_cost_sek_per_kwh: float | None = None
    energy_sources: EvEnergySourcesResponse
    renewable_share_percent: float
    grid_share_percent: float
    smart_charging_savings_sek: float | None = None
    solar_contribution_sek: float
    session_count: int
    savings_baseline: str = "IMMEDIATE_GRID_CHARGING"


class SolarSiteConfigResponse(BaseModel):
    site_slug: str
    latitude: float | None = None
    longitude: float | None = None
    installed_peak_power_kw: float | None = None
    azimuth_deg: float | None = None
    tilt_deg: float | None = None
    inverter_max_power_kw: float | None = None
    system_loss_percent: float = 14.0
    enabled: bool = False
    tilt_estimated: bool = False
    azimuth_estimated: bool = False
    complete: bool = False
    solar_intelligence_enabled: bool = False


class SolarSiteConfigUpdate(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    installed_peak_power_kw: float | None = None
    azimuth_deg: float | None = None
    tilt_deg: float | None = None
    inverter_max_power_kw: float | None = None
    system_loss_percent: float | None = Field(default=None, ge=0, le=50)
    enabled: bool = False
    tilt_estimated: bool = False
    azimuth_estimated: bool = False
    solar_intelligence_enabled: bool | None = None


class SolarForecastPointResponse(BaseModel):
    timestamp: datetime
    baseline_power_w: float
    corrected_power_w: float
    expected_energy_kwh: float
    lower_bound_power_w: float
    upper_bound_power_w: float
    confidence: float
    correction_factor: float = 1.0


class SolarForecastResponse(BaseModel):
    site_id: int
    generated_at: datetime
    model_version: str
    quality: str
    weather_source: str
    expected_today_kwh: float
    remaining_today_kwh: float
    expected_tomorrow_kwh: float | None = None
    peak_power_w: float
    peak_time: datetime | None = None
    confidence: float
    lower_today_kwh: float
    upper_today_kwh: float
    weather_summary: str
    actual_today_kwh: float = 0.0
    forecast_so_far_kwh: float = 0.0
    remaining_vs_expected_kwh: float = 0.0
    raw_forecast_today_kwh: float = 0.0
    raw_forecast_so_far_kwh: float = 0.0
    raw_forecast_tomorrow_kwh: float | None = None
    corrected_forecast_today_kwh: float = 0.0
    corrected_forecast_tomorrow_kwh: float | None = None
    correction_factor: float = 1.0
    model_state: str = "NO_DATA"
    confidence_score: float | None = None
    confidence_label: str | None = None
    historical_samples: int = 0
    production_days_observed: int = 0
    points: list[SolarForecastPointResponse] = Field(default_factory=list)


class SolarAccuracyResponse(BaseModel):
    site_slug: str
    model_version: str
    model_state: str = "NO_DATA"
    mape_7d_pct: float | None = None
    mape_30d_pct: float | None = None
    mape_7d_valid_days: int = 0
    mape_30d_valid_days: int = 0
    mae_kwh_7d: float | None = None
    mae_kwh_30d: float | None = None
    bias_pct_30d: float | None = None
    sample_count_30d: int = 0
    historical_samples: int = 0
    production_days_observed: int = 0
    correction_factor: float = 1.0
    confidence_score: float | None = None
    confidence_label: str | None = None
    metrics_insufficient: bool = True
    raw_mae_30d: float | None = None
    corrected_mae_30d: float | None = None
    improvement_pct_30d: float | None = None
    wape_7d_pct: float | None = None
    wape_30d_pct: float | None = None
    rmse_kwh_7d: float | None = None
    rmse_kwh_30d: float | None = None
    r2_30d: float | None = None
    insufficient_reason: str | None = None
    min_samples_for_calibrated: int = 30


class SolarForecastObservationResponse(BaseModel):
    forecast_date: date
    forecast_kwh_raw: float | None = None
    forecast_kwh_corrected: float | None = None
    actual_kwh: float | None = None
    absolute_error_kwh: float | None = None
    raw_absolute_error_kwh: float | None = None
    percentage_error: float | None = None
    data_completeness_pct: float | None = None
    correction_factor_used: float | None = None
    weather_condition_bucket: str | None = None
    training_eligible: bool = True
    exclusion_reason: str | None = None
    model_version: str


class SolarDiagnosticsResponse(BaseModel):
    site_slug: str
    observations: list[SolarForecastObservationResponse] = Field(default_factory=list)


class SolarEnergyBudgetResponse(BaseModel):
    site_slug: str
    forecast_solar_kwh: float
    expected_house_consumption_kwh: float | None = None
    expected_surplus_kwh: float | None = None
    expected_deficit_kwh: float | None = None
    confidence: float
    quality: str
    consumption_source: str = "unavailable"


class SolarHourlyPointResponse(BaseModel):
    timestamp: datetime
    physical_w: float
    corrected_w: float
    lower_w: float
    upper_w: float
    confidence: float


class SolarHourlyForecastResponse(BaseModel):
    site_slug: str
    points: list[SolarHourlyPointResponse] = Field(default_factory=list)


class SolarPerformanceResponse(BaseModel):
    site_slug: str
    days: list[dict] = Field(default_factory=list)
    headline_ratio: float | None = None
    today_deviation_pct: float | None = None
    week_avg: float | None = None
    month_avg: float | None = None
    quarter_avg: float | None = None
    ytd_avg: float | None = None
    raw_forecast_so_far_kwh: float | None = None
    actual_today_kwh: float | None = None


class SolarRadiationResponse(BaseModel):
    site_slug: str
    provider: str
    samples: list[dict] = Field(default_factory=list)


class DmiForecastPointResponse(BaseModel):
    timestamp: datetime
    ghi_wm2: float | None = None
    dhi_wm2: float | None = None
    temperature_c: float | None = None
    cloud_cover_pct: float | None = None
    precipitation_mm: float | None = None
    humidity_pct: float | None = None
    wind_speed_ms: float | None = None


class DmiForecastResponse(BaseModel):
    site_slug: str
    provider: str = "dmi-harmonie"
    country_code: str
    points: list[DmiForecastPointResponse] = Field(default_factory=list)


class SolarModelResponse(BaseModel):
    site_slug: str
    model_version: str | None = None
    sample_count: int = 0
    trained_at: datetime | None = None
    role: str | None = None


class SolarModelMetricsResponse(BaseModel):
    site_slug: str
    model_version: str
    mae: float | None = None
    mape: float | None = None
    wape: float | None = None
    rmse: float | None = None
    r2: float | None = None
    bias_pct: float | None = None
    metrics_insufficient: bool = True
    insufficient_reason: str | None = None
    historical_samples: int = 0


class SolarProviderStatusResponse(BaseModel):
    site_slug: str
    providers: list[dict] = Field(default_factory=list)


class SolarIntelligenceForecastResponse(BaseModel):
    site_slug: str
    expected_today_kwh: float = 0.0
    status: str = "UNAVAILABLE"
    point_count: int = 0


class SolarWeatherHourResponse(BaseModel):
    timestamp: datetime
    temperature_c: float | None = None
    cloud_cover_pct: float | None = None
    wind_speed_ms: float | None = None
    relative_humidity_pct: float | None = None
    precipitation_mm: float | None = None
    ghi_wm2: float | None = None
    weather_code: int | None = None
    condition_sv: str = "Okänt"
    condition_icon: str = "unknown"
    forecast_power_w: float | None = None


class SolarWeatherResponse(BaseModel):
    site_slug: str
    provider: str
    source: str
    fetched_at: datetime
    cache_age_minutes: float = 0.0
    sunrise: datetime | None = None
    sunset: datetime | None = None
    current: SolarWeatherHourResponse | None = None
    solar_impact_sv: str = ""
    hours: list[SolarWeatherHourResponse] = Field(default_factory=list)


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


class DashboardSectionMeta(BaseModel):
    unavailable_reason: str | None = None


class DashboardSiteSection(BaseModel):
    slug: str
    name: str
    timezone: str


class DashboardFreshnessSection(BaseModel):
    updated_at: datetime | None = None
    data_age_seconds: int | None = None
    stale: bool = False


class DashboardLiveSection(DashboardSectionMeta):
    solar_production_w: float | None = None
    consumption_w: float | None = None
    grid_import_w: float | None = None
    grid_export_w: float | None = None
    battery_soc_pct: float | None = None
    battery_power_w: float | None = None
    battery_direction: str | None = None
    ev_power_w: float | None = None


class DashboardTodaySection(DashboardSectionMeta):
    produced_kwh: float | None = None
    consumed_kwh: float | None = None
    imported_kwh: float | None = None
    exported_kwh: float | None = None
    energy_cost_sek: float | None = None
    savings_sek: float | None = None


class DashboardEvSection(DashboardSectionMeta):
    available: bool = False
    charging: bool = False
    charging_mode: str | None = None
    display_status_sv: str | None = None
    power_w: float | None = None
    session_energy_kwh: float | None = None
    solar_share_pct: float | None = None
    estimated_cost_sek: float | None = None
    next_planned_charge_at: datetime | None = None


class DashboardSolarSection(DashboardSectionMeta):
    expected_today_kwh: float | None = None
    remaining_kwh: float | None = None
    peak_power_w: float | None = None
    peak_at: datetime | None = None
    confidence_pct: float | None = None
    inverter_max_power_kw: float | None = None


class DashboardPriceSection(DashboardSectionMeta):
    current_eur_kwh: float | None = None
    lowest_eur_kwh: float | None = None
    highest_eur_kwh: float | None = None
    tier: str | None = None


class DashboardOptimizationSection(DashboardSectionMeta):
    strategy_sv: str | None = None
    explanation_sv: str | None = None
    reasoning_steps: list[str] = Field(default_factory=list)
    solar_first: bool | None = None
    battery_soc_pct: float | None = None


class DashboardAlert(BaseModel):
    severity: str
    message_sv: str


class DashboardResponse(BaseModel):
    site: DashboardSiteSection
    freshness: DashboardFreshnessSection
    live: DashboardLiveSection | None = None
    today: DashboardTodaySection | None = None
    ev: DashboardEvSection | None = None
    solar: DashboardSolarSection | None = None
    price: DashboardPriceSection | None = None
    optimization: DashboardOptimizationSection | None = None
    alerts: list[DashboardAlert] = Field(default_factory=list)
    spa_integration_enabled: bool = False
    vehicle_integration_enabled: bool = False


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
    capabilities: VehicleCapabilitiesResponse
    halo_correlation: VehicleHaloCorrelationResponse | None = None


class VehicleListResponse(BaseModel):
    site_slug: str
    vehicles: list[VehicleListItemResponse] = Field(default_factory=list)


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


class VehicleChargeSessionResponse(BaseModel):
    id: int
    vehicle_id: int
    charger_id: int
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


class VehicleChargeSessionListResponse(BaseModel):
    site_slug: str
    vehicle_id: int
    sessions: list[VehicleChargeSessionResponse] = Field(default_factory=list)


class HeartbeatDiscoveryRunResultResponse(BaseModel):
    run_id: int
    report_text: str
    setup_classification: str
    bridge_lifecycle: str
    resolved_ev_id: str | None
    confidence_pct: float
    virtual_bridge_suitable: bool
    charging_modes: list[str] = Field(default_factory=list)
    emic_vehicle_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class HeartbeatDiscoveryRunResponse(BaseModel):
    id: int
    status: str
    system_id: str | None
    conclusion_class: str | None
    bridge_lifecycle: str | None
    resolved_ev_id: str | None
    confidence_pct: float | None
    started_at: datetime
    completed_at: datetime | None


class HeartbeatDiscoveryRunDetailResponse(HeartbeatDiscoveryRunResponse):
    report_text: str
    report: dict[str, Any] = Field(default_factory=dict)
    observations: list[dict[str, Any]] = Field(default_factory=list)


class HeartbeatBridgeStatusResponse(BaseModel):
    heartbeat_connection: str
    ev_profile: str
    ev_id: str | None
    confidence_pct: float | None
    physical_hb_wallbox: str
    charge_amps_halo: str
    halo_online: bool
    virtual_bridge: str
    setup_classification: str | None
    bridge_lifecycle: str
    simulation_mode: bool
    physical_control: str
    write_enabled: bool
    settings: dict[str, Any] = Field(default_factory=dict)
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class HeartbeatEvMappingResponse(BaseModel):
    id: int
    heartbeat_ev_id: str
    heartbeat_ev_name: str
    physical_charger_id: int | None
    vehicle_id: int | None
    provider: str
    enabled: bool
    confidence_pct: float
    last_discovery_at: datetime | None


class HeartbeatEvMappingUpdateRequest(BaseModel):
    enabled: bool | None = None
    physical_charger_id: int | None = None
    vehicle_id: int | None = None


class HeartbeatBridgeSettingsResponse(BaseModel):
    site_id: int
    discovery_enabled: bool
    write_enabled: bool
    virtual_bridge_enabled: bool
    physical_control_enabled: bool
    soc_sync_enabled: bool
    replay_enabled: bool
    simulation_mode: bool
    confidence_threshold_pct: float
    battery_priority_mode: str


class HeartbeatBridgeSettingsUpdateRequest(BaseModel):
    discovery_enabled: bool | None = None
    write_enabled: bool | None = None
    virtual_bridge_enabled: bool | None = None
    physical_control_enabled: bool | None = None
    soc_sync_enabled: bool | None = None
    replay_enabled: bool | None = None
    simulation_mode: bool | None = None
    confidence_threshold_pct: float | None = Field(default=None, ge=0, le=100)
    battery_priority_mode: str | None = None


class HeartbeatWriteTestResponse(BaseModel):
    classification: str
    requested_value: Any | None = None
    http_status: int | None = None
    read_back_value: Any | None = None
    rollback_verified: bool | None = None
    duration_ms: int | None = None
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = True


class HeartbeatReplayResponse(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    report_text: str = ""


class EnergyOrchestrationLoadResponse(BaseModel):
    load_id: str
    name: str
    load_type: str
    priority: int
    strategy: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    expected_energy_kwh: float | None = None
    expected_cost_sek: float | None = None
    expected_energy_source: str | None = None
    reason_sv: str | None = None
    explanation_sv: str | None = None
    dry_run: bool = True


class EnergyOrchestrationResponse(BaseModel):
    site_slug: str
    loads: list[EnergyOrchestrationLoadResponse] = Field(default_factory=list)


class EnergyOrchestrationPriorityItem(BaseModel):
    load_id: str
    priority: int = Field(ge=0, le=100)


class EnergyOrchestrationPrioritiesUpdateRequest(BaseModel):
    loads: list[EnergyOrchestrationPriorityItem] = Field(default_factory=list)
