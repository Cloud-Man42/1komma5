"""Static configuration schemas for onboardable integration modules."""

from __future__ import annotations

from typing import Any

HEARTBEAT_CONFIG_SCHEMA: dict[str, Any] = {
    "fields": [
        {
            "name": "external_system_id",
            "label": "Heartbeat system ID",
            "type": "string",
            "required": True,
            "help": "External system identifier for this site in Heartbeat.",
        },
    ]
}

CHARGEAMPS_CONFIG_SCHEMA: dict[str, Any] = {
    "fields": [
        {
            "name": "api_key",
            "label": "API key",
            "type": "secret",
            "secret": True,
            "required": False,
            "help": "Charge Amps API key. Leave blank to keep existing value.",
        },
        {
            "name": "email",
            "label": "Account email",
            "type": "string",
            "required": False,
        },
        {
            "name": "password",
            "label": "Account password",
            "type": "secret",
            "secret": True,
            "required": False,
        },
    ]
}

MERCEDES_CONFIG_SCHEMA: dict[str, Any] = {
    "fields": [
        {
            "name": "username",
            "label": "Mercedes account email",
            "type": "string",
            "required": True,
        },
        {
            "name": "password",
            "label": "Mercedes account password",
            "type": "secret",
            "secret": True,
            "required": False,
            "help": "Leave blank to keep existing password.",
        },
    ]
}

ARCTIC_SPA_CONFIG_SCHEMA: dict[str, Any] = {
    "fields": [
        {
            "name": "api_key",
            "label": "Arctic Spa API key",
            "type": "secret",
            "secret": True,
            "required": False,
        },
        {
            "name": "spa_id",
            "label": "Spa ID",
            "type": "string",
            "required": True,
        },
    ]
}

ONBOARDING_CATEGORIES: tuple[dict[str, Any], ...] = (
    {"id": "ev_charger", "label": "EV charger", "description": "Home or garage EV charging hardware"},
    {"id": "vehicle", "label": "Vehicle", "description": "Connected electric vehicle telematics"},
    {"id": "energy_provider", "label": "Energy provider", "description": "Site energy platform and telemetry"},
    {"id": "spa", "label": "Spa", "description": "Hot tub / spa integration"},
    {"id": "weather_service", "label": "Weather service", "description": "Weather data for solar forecasting"},
    {"id": "other", "label": "Other integration", "description": "Additional supported integrations"},
)
