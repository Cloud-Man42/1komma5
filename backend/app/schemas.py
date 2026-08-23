from datetime import date, datetime

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


class SpaStatusResponse(BaseModel):
    consumer_id: int
    site_slug: str
    online: bool
    water_temperature_c: float | None = None
    set_temperature_c: float | None = None
    heater_active: bool = False
    pump_label: str = "Pump: Av"
    filter_status: str | None = None
    errors: list[str] = Field(default_factory=list)
    current_power_w: float | None = None
    last_updated: datetime | None = None
    data_source: str = "ARCTIC_SPA_REST"
    data_quality: str = "MISSING"
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
    max_power_w: float | None = None
    avg_power_w: float | None = None
    heater_runtime_hours: float = 0.0
    pump_runtime_hours: float = 0.0
    avg_cost_sek_kwh: float | None = None
    has_data: bool = False


class SpaHistoryPoint(BaseModel):
    timestamp: datetime
    power_w: float | None = None
    energy_kwh: float | None = None
    cost_sek: float | None = None
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
    data_quality: str = "MISSING"
    measured_pct: float | None = None
    calculated_pct: float | None = None
    estimated_pct: float | None = None
    missing_pct: float | None = None
    last_error: str | None = None


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
