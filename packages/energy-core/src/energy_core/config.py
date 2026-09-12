from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class HeartbeatProviderKind(StrEnum):
    MOCK = "mock"
    ONEKOMMAFIVE = "onekommafive"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT, alias="APP_ENV")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./energy-dev.db",
        alias="DATABASE_URL",
    )
    heartbeat_provider: HeartbeatProviderKind = Field(
        default=HeartbeatProviderKind.MOCK,
        alias="HEARTBEAT_PROVIDER",
    )
    heartbeat_poll_interval: int = Field(default=30, ge=5, alias="HEARTBEAT_POLL_INTERVAL")
    heartbeat_api_url: str = Field(default="", alias="HEARTBEAT_API_URL")
    heartbeat_api_key: str = Field(default="", alias="HEARTBEAT_API_KEY")
    heartbeat_account_denmark_username: str = Field(default="", alias="HEARTBEAT_ACCOUNT_DENMARK_USERNAME")
    heartbeat_account_denmark_password: str = Field(default="", alias="HEARTBEAT_ACCOUNT_DENMARK_PASSWORD")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", alias="LOG_LEVEL")
    solar_forecast_horizon_hours: int = Field(default=48, ge=12, le=72, alias="SOLAR_FORECAST_HORIZON_HOURS")
    solar_forecast_extended_days: int = Field(default=7, ge=0, le=16, alias="SOLAR_FORECAST_EXTENDED_DAYS")
    solar_forecast_refresh_minutes: int = Field(default=30, ge=5, alias="SOLAR_FORECAST_REFRESH_MINUTES")
    solar_forecast_sync_refresh_on_read: bool = Field(
        default=False,
        alias="SOLAR_FORECAST_SYNC_REFRESH_ON_READ",
    )
    solar_weather_cache_minutes: int = Field(default=45, ge=15, alias="SOLAR_WEATHER_CACHE_MINUTES")
    solar_weather_stale_minutes: int = Field(default=90, ge=30, alias="SOLAR_WEATHER_STALE_MINUTES")
    solar_forecast_retention_days: int = Field(default=14, ge=1, alias="SOLAR_FORECAST_RETENTION_DAYS")
    eur_to_sek_rate: float = Field(default=11.0, gt=0.0, alias="EUR_TO_SEK_RATE")
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
    chargefinder_enabled: bool = Field(default=True, alias="CHARGEFINDER_ENABLED")
    chargefinder_mode: str = Field(default="WEB", alias="CHARGEFINDER_MODE")
    chargefinder_timeout_seconds: float = Field(default=15.0, ge=3.0, alias="CHARGEFINDER_TIMEOUT_SECONDS")
    chargefinder_search_radius_m: int = Field(default=150, ge=50, alias="CHARGEFINDER_SEARCH_RADIUS_M")
    chargefinder_cache_ttl_seconds: float = Field(default=604800.0, ge=3600.0, alias="CHARGEFINDER_CACHE_TTL_SECONDS")
    chargefinder_cooldown_seconds: float = Field(default=900.0, ge=60.0, alias="CHARGEFINDER_COOLDOWN_SECONDS")
    chargefinder_allowed_radius_options: str = Field(
        default="50,100,150,250,500",
        alias="CHARGEFINDER_ALLOWED_RADIUS_OPTIONS",
    )

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
    solar_forecast_min_training_completeness_pct: float = Field(
        default=80.0, ge=0.0, le=100.0, alias="SOLAR_FORECAST_MIN_TRAINING_COMPLETENESS_PCT"
    )
    solar_forecast_night_elevation_deg: float = Field(default=5.0, ge=0.0, alias="SOLAR_FORECAST_NIGHT_ELEVATION_DEG")
    smhi_strang_base_url: str = Field(
        default="https://opendata-download-metanalys.smhi.se/api/category/strang1g/version/1/geotype/point",
        alias="SMHI_STRANG_BASE_URL",
    )
    smhi_snow_base_url: str = Field(
        default="https://opendata-download-metanalys.smhi.se/api/category/snow1g/version/1/geotype/point",
        alias="SMHI_SNOW_BASE_URL",
    )
    smhi_timeout_seconds: float = Field(default=30.0, ge=5.0, alias="SMHI_TIMEOUT_SECONDS")
    dmi_edr_base_url: str = Field(
        default="https://opendataapi.dmi.dk/v1/forecastedr",
        alias="DMI_EDR_BASE_URL",
    )
    dmi_harmonie_collection: str = Field(default="harmonie_dini_sf", alias="DMI_HARMONIE_COLLECTION")
    dmi_timeout_seconds: float = Field(default=30.0, ge=5.0, alias="DMI_TIMEOUT_SECONDS")

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
    spa_active_cleaning_poll_interval_seconds: int = Field(
        default=15,
        ge=5,
        le=120,
        alias="SPA_ACTIVE_CLEANING_POLL_INTERVAL_SECONDS",
    )
    spa_planner_watchdog_seconds: int = Field(default=180, ge=60, le=900, alias="SPA_PLANNER_WATCHDOG_SECONDS")
    spa_energy_collection_enabled: bool = Field(default=True, alias="SPA_ENERGY_COLLECTION_ENABLED")
    spa_cost_calculation_enabled: bool = Field(default=True, alias="SPA_COST_CALCULATION_ENABLED")

    widget_stale_seconds: int = Field(default=120, ge=30, alias="WIDGET_STALE_SECONDS")
    widget_snapshot_cache_seconds: int = Field(default=15, ge=0, alias="WIDGET_SNAPSHOT_CACHE_SECONDS")
    widget_rate_limit_per_minute: int = Field(default=60, ge=1, alias="WIDGET_RATE_LIMIT_PER_MINUTE")
    enable_timescaledb: bool = Field(default=False, alias="ENABLE_TIMESCALEDB")
    emic_admin_token: str = Field(default="", alias="EMIC_ADMIN_TOKEN")
    emic_user_auth_enabled: bool = Field(default=True, alias="EMIC_USER_AUTH_ENABLED")
    emic_bootstrap_admin_email: str = Field(default="", alias="EMIC_BOOTSTRAP_ADMIN_EMAIL")
    emic_bootstrap_admin_password: str = Field(default="", alias="EMIC_BOOTSTRAP_ADMIN_PASSWORD")
    emic_session_ttl_hours: int = Field(default=8, ge=1, le=720, alias="EMIC_SESSION_TTL_HOURS")
    emic_session_slide_minutes: int = Field(default=30, ge=5, le=240, alias="EMIC_SESSION_SLIDE_MINUTES")
    emic_login_max_attempts: int = Field(default=5, ge=3, le=20, alias="EMIC_LOGIN_MAX_ATTEMPTS")
    emic_login_lockout_minutes: int = Field(default=15, ge=1, le=1440, alias="EMIC_LOGIN_LOCKOUT_MINUTES")
    emic_login_rate_limit_per_minute: int = Field(default=20, ge=5, alias="EMIC_LOGIN_RATE_LIMIT_PER_MINUTE")
    emic_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="EMIC_CORS_ORIGINS",
    )
    emic_cookie_secure: bool = Field(default=False, alias="EMIC_COOKIE_SECURE")
    financial_aggregates_enabled: bool = Field(default=False, alias="FINANCIAL_AGGREGATES_ENABLED")
    redis_url: str = Field(default="", alias="REDIS_URL")
    snapshot_redis_cache_ttl_seconds: float = Field(default=60.0, ge=5.0, alias="SNAPSHOT_REDIS_CACHE_TTL_SECONDS")
    dashboard_redis_cache_ttl_seconds: float = Field(default=60.0, ge=5.0, alias="DASHBOARD_REDIS_CACHE_TTL_SECONDS")
    financial_redis_cache_ttl_seconds: float = Field(default=300.0, ge=30.0, alias="FINANCIAL_REDIS_CACHE_TTL_SECONDS")
    solar_forecast_redis_cache_ttl_seconds: float = Field(
        default=1800.0, ge=60.0, alias="SOLAR_FORECAST_REDIS_CACHE_TTL_SECONDS"
    )
    solar_forecast_l1_warm_ttl_seconds: float = Field(
        default=300.0, ge=5.0, alias="SOLAR_FORECAST_L1_WARM_TTL_SECONDS"
    )
    current_price_redis_cache_ttl_seconds: float = Field(
        default=120.0, ge=15.0, alias="CURRENT_PRICE_REDIS_CACHE_TTL_SECONDS"
    )
    horizon_optimizer_redis_cache_ttl_seconds: float = Field(
        default=300.0, ge=30.0, alias="HORIZON_OPTIMIZER_REDIS_CACHE_TTL_SECONDS"
    )
    energy_control_collector_enabled: bool = Field(default=True, alias="ENERGY_CONTROL_COLLECTOR_ENABLED")
    module_gate_enabled: bool = Field(default=True, alias="EMIC_MODULE_GATE_ENABLED")
    emic_modules_path: str = Field(default="", alias="EMIC_MODULES_PATH")
    emic_allow_unsigned_modules: bool = Field(default=False, alias="EMIC_ALLOW_UNSIGNED_MODULES")
    emic_version: str = Field(default="0.1.0", alias="EMIC_VERSION")
    emic_module_api_version: int = Field(default=1, ge=1, alias="EMIC_MODULE_API_VERSION")
    emic_module_package_max_bytes: int = Field(default=52_428_800, ge=1024, alias="EMIC_MODULE_PACKAGE_MAX_BYTES")
    emic_module_catalog_path: str = Field(default="", alias="EMIC_MODULE_CATALOG_PATH")
    marketplace_metadata_enabled: bool = Field(default=False, alias="MARKETPLACE_METADATA_ENABLED")
    marketplace_metadata_url: str = Field(default="", alias="MARKETPLACE_METADATA_URL")
    marketplace_targets_url: str = Field(default="", alias="MARKETPLACE_TARGETS_URL")
    marketplace_trusted_root_path: str = Field(default="", alias="MARKETPLACE_TRUSTED_ROOT_PATH")
    marketplace_sync_interval_seconds: int = Field(default=3600, ge=60, alias="MARKETPLACE_SYNC_INTERVAL_SECONDS")
    marketplace_metadata_max_bytes: int = Field(default=1_048_576, ge=1024, alias="MARKETPLACE_METADATA_MAX_BYTES")
    marketplace_connect_timeout_seconds: float = Field(default=5.0, ge=1.0, alias="MARKETPLACE_CONNECT_TIMEOUT_SECONDS")
    marketplace_read_timeout_seconds: float = Field(default=15.0, ge=1.0, alias="MARKETPLACE_READ_TIMEOUT_SECONDS")
    marketplace_tuf_state_path: str = Field(default="", alias="MARKETPLACE_TUF_STATE_PATH")
    marketplace_artifact_max_bytes: int = Field(default=52_428_800, ge=1024, alias="MARKETPLACE_ARTIFACT_MAX_BYTES")
    marketplace_artifact_connect_timeout_seconds: float = Field(
        default=10.0, ge=1.0, alias="MARKETPLACE_ARTIFACT_CONNECT_TIMEOUT_SECONDS"
    )
    marketplace_artifact_read_timeout_seconds: float = Field(
        default=120.0, ge=1.0, alias="MARKETPLACE_ARTIFACT_READ_TIMEOUT_SECONDS"
    )
    marketplace_artifact_allow_redirects: bool = Field(default=False, alias="MARKETPLACE_ARTIFACT_ALLOW_REDIRECTS")
    marketplace_artifact_max_redirects: int = Field(default=0, ge=0, le=5, alias="MARKETPLACE_ARTIFACT_MAX_REDIRECTS")
    marketplace_artifact_tls_verify: bool = Field(default=True, alias="MARKETPLACE_ARTIFACT_TLS_VERIFY")
    marketplace_staging_path: str = Field(default="", alias="MARKETPLACE_STAGING_PATH")
    marketplace_internal_cidrs: str = Field(default="", alias="MARKETPLACE_INTERNAL_CIDRS")
    third_party_runtime_enabled: bool = Field(default=False, alias="THIRD_PARTY_RUNTIME_ENABLED")
    isolated_runtime_enabled: bool = Field(default=False, alias="ISOLATED_RUNTIME_ENABLED")
    isolated_runtime_socket_dir: str = Field(default="", alias="ISOLATED_RUNTIME_SOCKET_DIR")
    isolated_runtime_data_root: str = Field(default="", alias="ISOLATED_RUNTIME_DATA_ROOT")
    isolated_runtime_sandbox: str = Field(default="auto", alias="ISOLATED_RUNTIME_SANDBOX")
    isolated_runtime_memory_mb: int = Field(default=256, ge=32, alias="ISOLATED_RUNTIME_MEMORY_MB")
    isolated_runtime_cpu_quota_percent: int = Field(default=50, ge=1, le=100, alias="ISOLATED_RUNTIME_CPU_QUOTA_PERCENT")
    isolated_runtime_max_processes: int = Field(default=32, ge=1, alias="ISOLATED_RUNTIME_MAX_PROCESSES")
    isolated_runtime_max_open_files: int = Field(default=256, ge=16, alias="ISOLATED_RUNTIME_MAX_OPEN_FILES")
    isolated_runtime_startup_timeout_seconds: float = Field(default=30.0, ge=5.0, alias="ISOLATED_RUNTIME_STARTUP_TIMEOUT_SECONDS")
    isolated_runtime_handshake_timeout_seconds: float = Field(default=15.0, ge=1.0, alias="ISOLATED_RUNTIME_HANDSHAKE_TIMEOUT_SECONDS")
    isolated_runtime_heartbeat_interval_seconds: float = Field(default=10.0, ge=1.0, alias="ISOLATED_RUNTIME_HEARTBEAT_INTERVAL_SECONDS")
    isolated_runtime_heartbeat_miss_threshold: int = Field(default=3, ge=1, alias="ISOLATED_RUNTIME_HEARTBEAT_MISS_THRESHOLD")
    isolated_runtime_max_restarts: int = Field(default=3, ge=0, alias="ISOLATED_RUNTIME_MAX_RESTARTS")
    isolated_runtime_restart_backoff_seconds: float = Field(
        default=5.0, ge=0.5, alias="ISOLATED_RUNTIME_RESTART_BACKOFF_SECONDS"
    )
    isolated_runtime_control_lease_ttl_seconds: float = Field(
        default=30.0, ge=1.0, alias="ISOLATED_RUNTIME_CONTROL_LEASE_TTL_SECONDS"
    )
    isolated_runtime_data_quota_mb: int = Field(default=128, ge=8, alias="ISOLATED_RUNTIME_DATA_QUOTA_MB")
    isolated_runtime_cpu_time_limit_seconds: int = Field(
        default=300, ge=10, alias="ISOLATED_RUNTIME_CPU_TIME_LIMIT_SECONDS"
    )
    isolated_runtime_rpc_max_bytes: int = Field(default=1_048_576, ge=1024, alias="ISOLATED_RUNTIME_RPC_MAX_BYTES")
    isolated_runtime_rpc_rate_limit_per_minute: int = Field(default=600, ge=1, alias="ISOLATED_RUNTIME_RPC_RATE_LIMIT_PER_MINUTE")
    isolated_runtime_rpc_max_concurrent: int = Field(default=16, ge=1, alias="ISOLATED_RUNTIME_RPC_MAX_CONCURRENT")
    isolated_runtime_module_uid: int = Field(default=10001, ge=1, alias="ISOLATED_RUNTIME_MODULE_UID")
    isolated_runtime_module_gid: int = Field(default=10001, ge=1, alias="ISOLATED_RUNTIME_MODULE_GID")
    isolated_runtime_protocol_version: int = Field(default=1, ge=1, alias="ISOLATED_RUNTIME_PROTOCOL_VERSION")
    energy_control_provider: str = Field(default="noop", alias="ENERGY_CONTROL_PROVIDER")
    timescale_retention_enabled: bool = Field(default=False, alias="TIMESCALE_RETENTION_ENABLED")
    timescale_compression_enabled: bool = Field(default=False, alias="TIMESCALE_COMPRESSION_ENABLED")
    collector_medium_lane_interval: int = Field(default=300, ge=30, alias="COLLECTOR_MEDIUM_LANE_INTERVAL")
    collector_slow_lane_interval: int = Field(default=900, ge=60, alias="COLLECTOR_SLOW_LANE_INTERVAL")
    collector_lane_timeout_seconds: int = Field(default=120, ge=30, alias="COLLECTOR_LANE_TIMEOUT_SECONDS")

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

    def resolved_modules_path(self) -> str:
        if self.emic_modules_path.strip():
            return self.emic_modules_path.strip()
        import sys
        from pathlib import Path

        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local" / "emic" / "modules"
        else:
            base = Path("/var/lib/emic/modules")
        if self.is_test or self.is_development:
            base = Path.cwd() / ".emic-modules"
        return str(base)

    def resolved_catalog_path(self) -> str:
        if self.emic_module_catalog_path.strip():
            return self.emic_module_catalog_path.strip()
        from pathlib import Path

        repo_catalog = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "modules" / "catalog"
        if repo_catalog.exists():
            return str(repo_catalog)
        return str(Path(self.resolved_modules_path()) / "catalog")

    def resolved_marketplace_trusted_root_path(self) -> str:
        if self.marketplace_trusted_root_path.strip():
            return self.marketplace_trusted_root_path.strip()
        from pathlib import Path

        fixture = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "marketplace_tuf"
            / "pinned_root.json"
        )
        if fixture.exists():
            return str(fixture)
        return str(Path(self.resolved_modules_path()) / "marketplace" / "pinned_root.json")

    def resolved_marketplace_tuf_state_path(self) -> str:
        if self.marketplace_tuf_state_path.strip():
            return self.marketplace_tuf_state_path.strip()
        import sys
        from pathlib import Path

        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local" / "emic" / "marketplace" / "tuf-state"
        else:
            base = Path("/var/lib/emic/marketplace/tuf-state")
        if self.is_test or self.is_development:
            base = Path.cwd() / ".emic-marketplace-tuf"
        return str(base)

    def resolved_marketplace_staging_path(self) -> str:
        if self.marketplace_staging_path.strip():
            return self.marketplace_staging_path.strip()
        import sys
        from pathlib import Path

        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local" / "emic" / "module-staging"
        else:
            base = Path("/var/lib/emic/module-staging")
        if self.is_test or self.is_development:
            base = Path.cwd() / "data" / "module-staging"
        return str(base)

    def marketplace_internal_cidrs_list(self) -> list[str]:
        if not self.marketplace_internal_cidrs.strip():
            return []
        return [part.strip() for part in self.marketplace_internal_cidrs.split(",") if part.strip()]

    def resolved_isolated_runtime_socket_dir(self) -> str:
        if self.isolated_runtime_socket_dir.strip():
            return self.isolated_runtime_socket_dir.strip()
        import sys
        from pathlib import Path

        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local" / "emic" / "runtime-sockets"
        else:
            base = Path("/var/lib/emic/runtime/sockets")
        if self.is_test or self.is_development:
            base = Path.cwd() / "data" / "runtime-sockets"
        return str(base)

    def resolved_isolated_runtime_data_root(self) -> str:
        if self.isolated_runtime_data_root.strip():
            return self.isolated_runtime_data_root.strip()
        import sys
        from pathlib import Path

        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local" / "emic" / "runtime-data"
        else:
            base = Path("/var/lib/emic/runtime/data")
        if self.is_test or self.is_development:
            base = Path.cwd() / "data" / "runtime-data"
        return str(base)

    def resolved_isolated_runtime_sandbox(self) -> str:
        mode = (self.isolated_runtime_sandbox or "auto").strip().lower()
        import sys

        if mode == "auto":
            return "bwrap" if sys.platform != "win32" else "subprocess"
        return mode

    def runtime_spawn_allowed(self) -> bool:
        return self.third_party_runtime_enabled or (
            self.isolated_runtime_enabled and not self.is_production
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnvironment.PRODUCTION


def assert_emic_admin_token_production_safe(
    *,
    app_env: str,
    emic_admin_token: str,
    emic_user_auth_enabled: bool = True,
) -> None:
    if app_env.lower() != "production":
        return
    if emic_user_auth_enabled:
        return
    if not (emic_admin_token or "").strip():
        raise RuntimeError("EMIC_ADMIN_TOKEN is required in production when EMIC_USER_AUTH_ENABLED=false")


def cors_origins_list(settings: Settings) -> list[str]:
    return [part.strip() for part in settings.emic_cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
