"""Arctic Spa configuration and power inference profiles."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from energy_core.config import get_settings


@dataclass(frozen=True, slots=True)
class SpaPowerProfiles:
    heater_w: float = 3000.0
    pump_low_w: float = 150.0
    pump_high_w: float = 400.0
    circulation_w: float = 200.0
    blower_w: float = 250.0
    max_plausible_power_w: float = 6000.0

    @classmethod
    def from_json(cls, raw: str | None) -> SpaPowerProfiles:
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return cls()
        if not isinstance(data, dict):
            return cls()
        return cls(
            heater_w=float(data.get("heater_w", 3000.0)),
            pump_low_w=float(data.get("pump_low_w", 150.0)),
            pump_high_w=float(data.get("pump_high_w", 400.0)),
            circulation_w=float(data.get("circulation_w", 200.0)),
            blower_w=float(data.get("blower_w", 250.0)),
            max_plausible_power_w=float(data.get("max_plausible_power_w", 6000.0)),
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "heater_w": self.heater_w,
                "pump_low_w": self.pump_low_w,
                "pump_high_w": self.pump_high_w,
                "circulation_w": self.circulation_w,
                "blower_w": self.blower_w,
                "max_plausible_power_w": self.max_plausible_power_w,
            }
        )


@dataclass(frozen=True, slots=True)
class ArcticSpaConfiguration:
    enabled: bool
    api_base_url: str
    api_key: str
    external_spa_id: str
    poll_interval_seconds: int
    energy_collection_enabled: bool
    cost_calculation_enabled: bool
    power_profiles: SpaPowerProfiles

    @classmethod
    def from_env(cls) -> ArcticSpaConfiguration:
        settings = get_settings()
        return cls(
            enabled=settings.arctic_spa_enabled,
            api_base_url=settings.arctic_spa_api_base_url.rstrip("/"),
            api_key=settings.arctic_spa_api_key or os.getenv("ARCTIC_SPA_API_KEY", ""),
            external_spa_id=settings.arctic_spa_id,
            poll_interval_seconds=settings.arctic_spa_poll_interval_seconds,
            energy_collection_enabled=settings.spa_energy_collection_enabled,
            cost_calculation_enabled=settings.spa_cost_calculation_enabled,
            power_profiles=SpaPowerProfiles(),
        )

    @classmethod
    def merge(
        cls,
        *,
        db_enabled: bool,
        db_base_url: str,
        db_api_key: str,
        db_spa_id: str,
        db_poll_interval: int,
        db_energy_enabled: bool,
        db_cost_enabled: bool,
        db_profiles_json: str,
        env: ArcticSpaConfiguration | None = None,
    ) -> ArcticSpaConfiguration:
        env = env or cls.from_env()
        api_key = db_api_key or env.api_key
        return cls(
            enabled=db_enabled and env.enabled,
            api_base_url=(db_base_url or env.api_base_url).rstrip("/"),
            api_key=api_key,
            external_spa_id=db_spa_id or env.external_spa_id,
            poll_interval_seconds=db_poll_interval or env.poll_interval_seconds,
            energy_collection_enabled=db_energy_enabled and env.energy_collection_enabled,
            cost_calculation_enabled=db_cost_enabled and env.cost_calculation_enabled,
            power_profiles=SpaPowerProfiles.from_json(db_profiles_json),
        )


def mask_api_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"
