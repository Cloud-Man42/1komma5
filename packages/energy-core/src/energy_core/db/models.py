from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SiteModel(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    external_system_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fallback_purchase_price_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    export_compensation_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    main_fuse_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_margin_a: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)

    readings: Mapped[list["EnergyReadingModel"]] = relationship(back_populates="site")
    market_prices: Mapped[list["MarketPriceModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    historical_monthly_energy: Mapped[list["HistoricalMonthlyEnergyModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    ev_chargers: Mapped[list["EvChargerModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    solar_configuration: Mapped["SolarSiteConfigurationModel | None"] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
        uselist=False,
    )


class EvChargerModel(Base):
    __tablename__ = "ev_chargers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="ChargeAmps")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="Halo")
    control_source: Mapped[str] = mapped_column(String(16), nullable=False, default="chargeamp")
    heartbeat_ev_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_charger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chargeamp_charger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacturer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    integration_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_charger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connection_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_CONFIGURED")
    last_connection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connection_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bridge_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_current_a: Mapped[float] = mapped_column(Float, nullable=False, default=16.0)
    min_current_a: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    phases: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    nominal_voltage_v: Mapped[float] = mapped_column(Float, nullable=False, default=230.0)
    max_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_grid_import_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    update_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    min_change_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    current_hysteresis_a: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    stale_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    chargeamps_api_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    last_applied_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_bridge_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    target_soc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    solar_start_threshold_w: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    solar_stop_threshold_w: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    solar_start_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    solar_stop_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_charging_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_charging_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_charger_error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_halo_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_vehicle_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smart_charging_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_requested_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_configured_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_actual_charging_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_actual_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    externally_limited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_stop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    stop_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    minimum_run_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    minimum_off_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    temporary_grid_import_allowance_w: Mapped[float] = mapped_column(Float, nullable=False, default=800.0)
    temporary_grid_import_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    grid_deadband_w: Mapped[float] = mapped_column(Float, nullable=False, default=300.0)
    minimum_current_change_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_current_increase_per_step_a: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    max_current_decrease_per_step_a: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    max_automatic_starts_per_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    virtual_evse_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    semp_device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    semp_endpoint_registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="ev_chargers")
    bridge_cycles: Mapped[list["EvBridgeCycleModel"]] = relationship(
        back_populates="charger",
        cascade="all, delete-orphan",
    )
    charging_sessions: Mapped[list["EvChargingSessionModel"]] = relationship(
        back_populates="charger",
        cascade="all, delete-orphan",
    )


class EvChargingSessionModel(Base):
    __tablename__ = "ev_charging_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    meter_start_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    meter_stop_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    smart_charging_savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_contribution_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cost_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    attribution_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    savings_baseline: Mapped[str] = mapped_column(String(32), nullable=False, default="IMMEDIATE_GRID_CHARGING")
    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False, default="ev-energy-v1")
    reconciliation_delta_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    reconciliation_note: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chargeamps_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    charger: Mapped[EvChargerModel] = relationship(back_populates="charging_sessions")
    intervals: Mapped[list["EvChargingIntervalModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class EvChargingIntervalModel(Base):
    __tablename__ = "ev_charging_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ev_charging_sessions.id", ondelete="CASCADE"), nullable=False)
    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    charged_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_charging_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    pv_production_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    house_consumption_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_import_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_export_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_charge_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_discharge_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    electricity_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)

    session: Mapped[EvChargingSessionModel] = relationship(back_populates="intervals")


class BatteryEnergyLedgerModel(Base):
    __tablename__ = "battery_energy_ledger"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    solar_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_energy_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class EvBridgeCycleModel(Base):
    __tablename__ = "ev_bridge_cycles"

    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    applied_current_a: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    decision_reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    override_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vehicle_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    charger: Mapped[EvChargerModel] = relationship(back_populates="bridge_cycles")


class EnergyReadingModel(Base):
    __tablename__ = "energy_readings"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    solar_production_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumption_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_import_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_export_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    battery_soc_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    battery_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ev_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_charge_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_discharge_w: Mapped[float | None] = mapped_column(Float, nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="readings")


class MarketPriceModel(Base):
    __tablename__ = "market_prices"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    spot_price_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    all_in_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="market_prices")


class HistoricalMonthlyEnergyModel(Base):
    __tablename__ = "historical_monthly_energy"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, primary_key=True)
    imported_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    imported_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    site: Mapped[SiteModel] = relationship(back_populates="historical_monthly_energy")


class SolarSiteConfigurationModel(Base):
    __tablename__ = "solar_site_configurations"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    installed_peak_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    azimuth_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    tilt_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    inverter_max_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    system_loss_percent: Mapped[float] = mapped_column(Float, nullable=False, default=14.0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tilt_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    azimuth_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_forecast_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="solar_configuration")


class SolarWeatherCacheModel(Base):
    __tablename__ = "solar_weather_cache"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="open-meteo")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SolarForecastRunModel(Base):
    __tablename__ = "solar_forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v1")
    quality: Mapped[str] = mapped_column(String(32), nullable=False, default="LOW")
    weather_source: Mapped[str] = mapped_column(String(16), nullable=False, default="live")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    remaining_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_tomorrow_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    peak_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lower_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_today_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weather_summary: Mapped[str] = mapped_column(String(256), nullable=False, default="")


class SolarForecastPointModel(Base):
    __tablename__ = "solar_forecast_points"

    run_id: Mapped[int] = mapped_column(ForeignKey("solar_forecast_runs.id", ondelete="CASCADE"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    baseline_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    corrected_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lower_bound_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_bound_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correction_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    gti_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class SolarForecastEvaluationModel(Base):
    __tablename__ = "solar_forecast_evaluations"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    forecasted_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    absolute_error_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    squared_error: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v1")


class SolarSitePerformanceProfileModel(Base):
    __tablename__ = "solar_site_performance_profiles"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    global_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    seasonal_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    hour_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    weather_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mape_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_kwh_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_pct_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastObservationModel(Base):
    __tablename__ = "solar_forecast_observations"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    forecast_date: Mapped[date] = mapped_column(Date, primary_key=True)
    forecast_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    forecast_kwh_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_kwh_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weather_model: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cloud_cover_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_hourly_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    solar_radiation: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation: Mapped[float | None] = mapped_column(Float, nullable=True)
    sunshine_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    sunrise: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sunset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    weather_condition_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correction_factor_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_error_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    signed_error_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_absolute_error_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_percentage_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_completeness_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v2")
    site_configuration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastModelProfileModel(Base):
    __tablename__ = "solar_forecast_model_profiles"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v2")
    historical_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_state: Mapped[str] = mapped_column(String(32), nullable=False, default="NO_DATA")
    mape_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape_7d_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mape_30d_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mape_90d_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mae_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_mae_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_mae_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    improvement_pct_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    correction_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    seasonal_factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_training_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarArrayModel(Base):
    __tablename__ = "solar_arrays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Main")
    capacity_kwp: Mapped[float] = mapped_column(Float, nullable=False)
    azimuth_degrees: Mapped[float] = mapped_column(Float, nullable=False, default=180.0)
    tilt_degrees: Mapped[float] = mapped_column(Float, nullable=False, default=35.0)


class SolarSiteConfigurationVersionModel(Base):
    __tablename__ = "solar_site_configuration_versions"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    config_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class SiteEnergyConfigModel(Base):
    __tablename__ = "site_energy_config"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    load_includes_ev_charger: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    inverter_display_name: Mapped[str] = mapped_column(
        String(128), nullable=False, default="Sungrow Hybrid Inverter SH10"
    )
    physical_ev_charger_label: Mapped[str] = mapped_column(String(128), nullable=False, default="Charge Amps Halo")
    ev_vehicle_label: Mapped[str] = mapped_column(String(128), nullable=False, default="Mercedes EQE 500")


class EnergyBalanceSnapshotModel(Base):
    __tablename__ = "energy_balance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class HeartbeatSettingsModel(Base):
    __tablename__ = "heartbeat_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    connection_type: Mapped[str] = mapped_column(String(16), nullable=False, default="mock")
    host: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=443)
    use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    api_path: Mapped[str] = mapped_column(String(128), nullable=False, default="/api")
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    dashboard_refresh_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    password: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EnergyConsumerModel(Base):
    __tablename__ = "energy_consumers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    consumer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="SPA")
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Arctic Spa")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Stockholm")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SpaDeviceConfigModel(Base):
    __tablename__ = "spa_device_config"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    integration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_base_url: Mapped[str] = mapped_column(String(255), nullable=False, default="https://api.myarcticspa.com")
    api_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    external_spa_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    energy_collection_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cost_calculation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    power_profiles_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_status_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SpaPollStateModel(Base):
    __tablename__ = "spa_poll_state"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sample_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    polling_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ConsumerSampleModel(Base):
    __tablename__ = "consumer_samples"

    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_delta_wh: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    set_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    heater_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pump_states_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    filter_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spa_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="ARCTIC_SPA_REST")
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="CALCULATED")
    component_breakdown_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class ConsumerIntervalModel(Base):
    __tablename__ = "consumer_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    pv_production_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    house_consumption_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_import_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_export_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_charge_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_discharge_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    electricity_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unknown_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    heater_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pump_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)


class ConsumerAggregateModel(Base):
    __tablename__ = "consumer_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), nullable=False)
    granularity: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unknown_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    heater_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pump_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    measured_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
