from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from energy_core.paths import default_env_file, resolve_database_url


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class HeartbeatProviderKind(StrEnum):
    MOCK = "mock"
    ONEKOMMAFIVE = "onekommafive"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Anchored at the project root rather than left relative, so every
        # entry point reads the same file no matter which directory it was
        # started from -- see `energy_core.paths` (GH-53).
        env_file=default_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT, alias="APP_ENV")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./energy-dev.db",
        alias="DATABASE_URL",
        # The default is as relative as the value `.env.example` documents,
        # so it needs the same anchoring every other source of this field
        # gets; pydantic skips validators on defaults unless asked (GH-53).
        validate_default=True,
    )
    heartbeat_provider: HeartbeatProviderKind = Field(
        default=HeartbeatProviderKind.MOCK,
        alias="HEARTBEAT_PROVIDER",
    )
    heartbeat_poll_interval: int = Field(default=30, ge=5, alias="HEARTBEAT_POLL_INTERVAL")
    heartbeat_api_url: str = Field(default="", alias="HEARTBEAT_API_URL")
    heartbeat_api_key: str = Field(default="", alias="HEARTBEAT_API_KEY")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", alias="LOG_LEVEL")
    solar_forecast_horizon_hours: int = Field(default=48, ge=12, le=72, alias="SOLAR_FORECAST_HORIZON_HOURS")
    solar_forecast_refresh_minutes: int = Field(default=30, ge=5, alias="SOLAR_FORECAST_REFRESH_MINUTES")
    solar_weather_cache_minutes: int = Field(default=45, ge=15, alias="SOLAR_WEATHER_CACHE_MINUTES")
    solar_weather_stale_minutes: int = Field(default=90, ge=30, alias="SOLAR_WEATHER_STALE_MINUTES")
    solar_forecast_retention_days: int = Field(default=14, ge=1, alias="SOLAR_FORECAST_RETENTION_DAYS")
    open_meteo_base_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        alias="OPEN_METEO_BASE_URL",
    )
    open_meteo_historical_url: str = Field(
        default="https://archive-api.open-meteo.com/v1/archive",
        alias="OPEN_METEO_HISTORICAL_URL",
    )
    open_meteo_api_key: str = Field(default="", alias="OPEN_METEO_API_KEY")
    open_meteo_timeout_seconds: float = Field(default=30.0, ge=5.0, alias="OPEN_METEO_TIMEOUT_SECONDS")

    # Solar forecast v2 calibration thresholds
    solar_forecast_min_samples_preliminary: int = Field(default=7, ge=1, alias="SOLAR_FORECAST_MIN_SAMPLES_PRELIMINARY")
    solar_forecast_min_samples_calibrated: int = Field(default=30, ge=1, alias="SOLAR_FORECAST_MIN_SAMPLES_CALIBRATED")
    solar_forecast_min_samples_mature: int = Field(default=60, ge=1, alias="SOLAR_FORECAST_MIN_SAMPLES_MATURE")
    solar_forecast_rolling_window_days: int = Field(default=60, ge=7, alias="SOLAR_FORECAST_ROLLING_WINDOW_DAYS")
    solar_forecast_mape_min_actual_kwh: float = Field(default=1.0, ge=0.0, alias="SOLAR_FORECAST_MAPE_MIN_ACTUAL_KWH")
    solar_forecast_min_data_completeness_pct: float = Field(
        default=95.0, ge=0.0, le=100.0, alias="SOLAR_FORECAST_MIN_DATA_COMPLETENESS_PCT"
    )
    solar_forecast_correction_factor_min: float = Field(default=0.70, gt=0.0, alias="SOLAR_FORECAST_CORRECTION_FACTOR_MIN")
    solar_forecast_correction_factor_max: float = Field(default=1.30, gt=0.0, alias="SOLAR_FORECAST_CORRECTION_FACTOR_MAX")
    solar_forecast_outlier_ratio_min: float = Field(default=0.30, ge=0.0, alias="SOLAR_FORECAST_OUTLIER_RATIO_MIN")
    solar_forecast_outlier_ratio_max: float = Field(default=1.70, ge=0.0, alias="SOLAR_FORECAST_OUTLIER_RATIO_MAX")
    solar_forecast_correction_ema_alpha: float = Field(default=0.15, gt=0.0, le=1.0, alias="SOLAR_FORECAST_CORRECTION_EMA_ALPHA")

    # Sungrow / energy balance / Virtual EVSE (Phase 1)
    sungrow_telemetry_max_age_seconds: float = Field(default=60.0, ge=5.0, alias="SUNGROW_TELEMETRY_MAX_AGE_SECONDS")
    max_telemetry_alignment_age_seconds: float = Field(default=10.0, ge=1.0, alias="MAX_TELEMETRY_ALIGNMENT_AGE_SECONDS")
    energy_balance_residual_warn_w: float = Field(default=500.0, ge=0.0, alias="ENERGY_BALANCE_RESIDUAL_WARN_W")
    double_counting_tolerance_w: float = Field(default=800.0, ge=0.0, alias="DOUBLE_COUNTING_TOLERANCE_W")
    virtual_evse_stale_seconds: float = Field(default=120.0, ge=30.0, alias="VIRTUAL_EVSE_STALE_SECONDS")

    # Arctic Spa integration
    arctic_spa_enabled: bool = Field(default=False, alias="ARCTIC_SPA_ENABLED")
    arctic_spa_api_base_url: str = Field(default="https://api.myarcticspa.com", alias="ARCTIC_SPA_API_BASE_URL")
    arctic_spa_api_key: str = Field(default="", alias="ARCTIC_SPA_API_KEY")
    arctic_spa_poll_interval_seconds: int = Field(default=60, ge=15, le=600, alias="ARCTIC_SPA_POLL_INTERVAL_SECONDS")
    arctic_spa_id: str = Field(default="", alias="ARCTIC_SPA_ID")
    spa_smart_control_enabled: bool = Field(default=False, alias="SPA_SMART_CONTROL_ENABLED")
    spa_energy_collection_enabled: bool = Field(default=True, alias="SPA_ENERGY_COLLECTION_ENABLED")
    spa_cost_calculation_enabled: bool = Field(default=True, alias="SPA_COST_CALCULATION_ENABLED")

    @field_validator("database_url")
    @classmethod
    def anchor_relative_sqlite_path(cls, value: str) -> str:
        """Make `database_url` name the same physical file regardless of the
        working directory it is read from. Absolute and non-sqlite URLs are
        returned unchanged -- see `energy_core.paths.resolve_database_url`."""
        return resolve_database_url(value)

    @field_validator("heartbeat_provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: str | HeartbeatProviderKind) -> HeartbeatProviderKind:
        if isinstance(value, HeartbeatProviderKind):
            return value
        return HeartbeatProviderKind(str(value).lower())

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnvironment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.app_env == AppEnvironment.TEST


@lru_cache
def get_settings() -> Settings:
    return Settings()
