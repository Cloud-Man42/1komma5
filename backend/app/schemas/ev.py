from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

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
