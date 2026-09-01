from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
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
    energy_economics_country: Mapped[str] = mapped_column(String(8), nullable=False, default="SE")
    sell_pricing_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="spot")
    sell_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    sell_adjustment_ore_per_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sell_deduction_ore_per_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_benefit_ore_per_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    historical_tax_credit_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sell_contract_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
    chargeamps_api_key: Mapped[str] = mapped_column("encrypted_chargeamps_api_key", Text, nullable=False, default="")
    last_applied_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_bridge_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    target_soc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    load_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
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
    spot_price_eur_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    all_in_price_eur_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    feed_in_price_eur_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)

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
    solar_intelligence_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    commissioning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    panel_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    panel_wp: Mapped[float | None] = mapped_column(Float, nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

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
    physical_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    learned_correction_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    radiation_kwh_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
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
    wape_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
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


class SolarDailyForecastSnapshotModel(Base):
    __tablename__ = "solar_daily_forecast_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    forecast_date: Mapped[date] = mapped_column(Date, primary_key=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_kwh_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_kwh_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("solar_forecast_runs.id", ondelete="SET NULL"), nullable=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="solar-forecast-v2")
    weather_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarRadiationSampleModel(Base):
    __tablename__ = "solar_radiation_samples"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    parameter: Mapped[str] = mapped_column(String(32), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    value_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="GOOD")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SolarWeatherSnapshotModel(Base):
    __tablename__ = "solar_weather_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarTrainingSampleModel(Base):
    __tablename__ = "solar_training_samples"
    __table_args__ = (
        UniqueConstraint("site_id", "sample_date", "hour_utc", name="uq_solar_training_sample"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_date: Mapped[date] = mapped_column(Date, nullable=False)
    hour_utc: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    physical_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    ghi_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    dni_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    dhi_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    poa_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_elevation_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="GOOD")
    provenance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SolarModelRecordModel(Base):
    __tablename__ = "solar_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="challenger")
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    features_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    coefficients_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    configuration_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarForecastHourlyModel(Base):
    __tablename__ = "solar_forecast_hourly"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    physical_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    corrected_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lower_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    breakdown_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SolarPerformanceDailyModel(Base):
    __tablename__ = "solar_performance_daily"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    performance_date: Mapped[date] = mapped_column(Date, primary_key=True)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_normalized_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolarProviderHealthModel(Base):
    __tablename__ = "solar_provider_health"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(256), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    password: Mapped[str] = mapped_column("encrypted_password", Text, nullable=False, default="")
    api_token: Mapped[str] = mapped_column("encrypted_api_token", Text, nullable=False, default="")
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
    api_key: Mapped[str] = mapped_column("encrypted_api_key", Text, nullable=False, default="")
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

    __table_args__ = (
        UniqueConstraint("consumer_id", "granularity", "period_start", name="uq_consumer_aggregates_period"),
    )

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


class SpaControlConfigModel(Base):
    __tablename__ = "spa_control_config"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    smart_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="SMART")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shadow_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shadow_mode_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    min_cleaning_hours_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    allowed_window_start: Mapped[str] = mapped_column(String(8), nullable=False, default="07:00")
    allowed_window_end: Mapped[str] = mapped_column(String(8), nullable=False, default="22:00")
    prefer_solar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_battery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_battery_soc_pct: Mapped[float] = mapped_column(Float, nullable=False, default=40.0)
    min_run_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    min_stop_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_starts_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    filter_cycles_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    filter_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    minimum_cycle_separation_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    filter_optimization_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_known_safe_filter_schedule_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_floor_frequency_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    safety_floor_duration_hours: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    smart_preheat_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    normal_temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=38.0)
    max_preheat_temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=39.0)
    min_comfort_temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=37.0)
    load_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    fixed_schedule_start: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fixed_schedule_end: Mapped[str | None] = mapped_column(String(8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SpaEnergyEventModel(Base):
    __tablename__ = "spa_energy_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stop_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runtime_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reason_sv: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="SMART")
    decision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shadow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SpaActuatorStateModel(Base):
    __tablename__ = "spa_actuator_state"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="IDLE")
    runtime_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    integration_degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integration_degraded_message_sv: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FlexibleLoadPlanModel(Base):
    __tablename__ = "flexible_load_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    consumer_id: Mapped[int | None] = mapped_column(ForeignKey("energy_consumers.id", ondelete="SET NULL"), nullable=True)
    load_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reason_sv: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    explanation_sv: Mapped[str] = mapped_column(Text, nullable=False, default="")
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_energy_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fallback_from_solar_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    windows_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FlexibleLoadPlanBlockModel(Base):
    __tablename__ = "flexible_load_plan_block"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("flexible_load_plan.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_forecast_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    house_load_forecast_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    available_surplus_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    marginal_cost_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_energy_source: Mapped[str] = mapped_column(String(16), nullable=False, default="GRID")
    price_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class VehicleProviderConnectionModel(Base):
    __tablename__ = "vehicle_provider_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mercedes")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, default="Europe")
    username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_guid: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")
    commands_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_error: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconnect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_429_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decode_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_token_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_polling_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class VehicleModel(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mercedes")
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    vin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="Mercedes-Benz")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    usable_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleCapabilityModel(Base):
    __tablename__ = "vehicle_capabilities"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    capability: Mapped[str] = mapped_column(String(64), primary_key=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="discovery")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleStateLatestModel(Base):
    __tablename__ = "vehicle_state_latest"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    state_of_charge_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    electric_range_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_plugged_in: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_charging: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charging_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_power_limit_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_charge_complete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    soc_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    range_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")
    data_quality: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    last_vehicle_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_provider_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleStateHistoryModel(Base):
    __tablename__ = "vehicle_state_history"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    state_of_charge_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    electric_range_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_plugged_in: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_charging: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charging_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")
    data_quality: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")


class VehicleHaloCorrelationModel(Base):
    __tablename__ = "vehicle_halo_correlation"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNAVAILABLE")
    plugged_agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charging_agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    power_delta_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    halo_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleChargeSessionModel(Base):
    __tablename__ = "vehicle_charge_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    ev_charging_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_soc: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_soc: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    meter_start_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    meter_stop_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    halo_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_battery_energy_delta_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    identification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cost_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    attribution_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    savings_baseline: Mapped[str] = mapped_column(String(32), nullable=False, default="IMMEDIATE_GRID_CHARGING")
    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False, default="vehicle-charge-v1")
    reconciliation_delta_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    reconciliation_note: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charger_operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charger_network: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    connector_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    home_charging: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    energy_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    estimated_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_power_avg_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_power_max_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    detection_confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    identification_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_data_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    charging_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    charging_station_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    station_provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    station_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    distance_from_vehicle_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    station_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    station_resolution_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    station_candidates_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    intervals: Mapped[list["VehicleChargingIntervalModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class VehicleChargingIntervalModel(Base):
    __tablename__ = "vehicle_charging_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("vehicle_charge_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
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

    session: Mapped[VehicleChargeSessionModel] = relationship(back_populates="intervals")


class VehicleAttributeObservationModel(Base):
    __tablename__ = "vehicle_attribute_observations"
    __table_args__ = (
        UniqueConstraint(
            "vehicle_id",
            "attribute_name",
            "source",
            name="uq_vehicle_attribute_obs_vehicle_name_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="WS")
    value_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    masked_sample: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class VehicleApiEventModel(Base):
    __tablename__ = "vehicle_api_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_provider_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="GET")
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VehicleIntegrationEventModel(Base):
    __tablename__ = "vehicle_integration_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ChargingLocationModel(Base):
    __tablename__ = "charging_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    expected_operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_network: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    price_model: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    price_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ChargingStationModel(Base):
    __tablename__ = "charging_station"
    __table_args__ = (UniqueConstraint("provider", "provider_station_id", name="uq_charging_station_provider_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False, default="CHARGEFINDER")
    provider_station_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    connector_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    external_station_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    network_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_provider_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ChargingStationLookupCacheModel(Base):
    __tablename__ = "charging_station_lookup_cache"

    geohash_key: Mapped[str] = mapped_column(String(12), primary_key=True)
    latitude_rounded: Mapped[float] = mapped_column(Float, nullable=False)
    longitude_rounded: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChargeFinderIntegrationStatusModel(Base):
    __tablename__ = "chargefinder_integration_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_lookup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cache_hits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_misses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parser_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lookup_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    browser_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parsing_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1")


class ChargingLocationObservationModel(Base):
    __tablename__ = "charging_location_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    location_name: Mapped[str] = mapped_column(String(128), nullable=False)
    charger_operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HeartbeatDiscoveryRunModel(Base):
    __tablename__ = "heartbeat_discovery_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    system_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    conclusion_class: Mapped[str | None] = mapped_column(String(8), nullable=True)
    bridge_lifecycle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_ev_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    report_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HeartbeatApiObservationModel(Base):
    __tablename__ = "heartbeat_api_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("heartbeat_discovery_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observation_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    schema_fingerprint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HeartbeatEvMappingModel(Base):
    __tablename__ = "heartbeat_ev_mappings"
    __table_args__ = (
        UniqueConstraint("site_id", "heartbeat_ev_id", name="uq_heartbeat_ev_mappings_site_ev"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    heartbeat_ev_id: Mapped[str] = mapped_column(String(128), nullable=False)
    heartbeat_ev_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    physical_charger_id: Mapped[int | None] = mapped_column(
        ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="heartbeat")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HeartbeatBridgeSettingsModel(Base):
    __tablename__ = "heartbeat_bridge_settings"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    discovery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    write_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    virtual_bridge_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    physical_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    soc_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replay_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    simulation_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_threshold_pct: Mapped[float] = mapped_column(Float, nullable=False, default=90.0)
    battery_priority_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="BATTERY_FIRST")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HeartbeatWriteTestModel(Base):
    __tablename__ = "heartbeat_write_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    heartbeat_ev_id: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VirtualChargerDecisionModel(Base):
    __tablename__ = "virtual_charger_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    heartbeat_ev_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bridge_state: Mapped[str] = mapped_column(String(64), nullable=False)
    heartbeat_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_decision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class VirtualChargerCommandModel(Base):
    __tablename__ = "virtual_charger_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class VirtualChargerReplayRunModel(Base):
    __tablename__ = "virtual_charger_replay_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    report_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppleDeviceModel(Base):
    __tablename__ = "apple_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_label: Mapped[str] = mapped_column(String(128), nullable=False)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    device_type: Mapped[str] = mapped_column(String(64), nullable=False, default="iphone")
    token_prefix: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[str] = mapped_column(String(256), nullable=False, default="widget.read")
    default_site_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SiteLiveSnapshotModel(Base):
    __tablename__ = "site_live_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    freshness: Mapped[str] = mapped_column(String(16), nullable=False, default="DEGRADED")
    source_status_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class EnergyHourlyModel(Base):
    __tablename__ = "energy_hourly"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    hour: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    solar_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class EnergyDailyModel(Base):
    __tablename__ = "energy_daily"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    solar_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    export_revenue_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
