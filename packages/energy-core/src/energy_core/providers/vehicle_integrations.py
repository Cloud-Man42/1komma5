"""Vehicle vendor wiring — factories and command helpers."""

from __future__ import annotations

from energy_core.integrations.mercedes.auth import MercedesAuthError
from energy_core.integrations.mercedes.commands import (
    MercedesCommandFeatures,
    build_charging_action_command,
    build_set_target_soc_command,
    describe_client_message,
)
from energy_core.integrations.mercedes.factory import (
    build_mercedes_provider,
    is_mercedes_provider,
    wire_supervisor_token_callbacks,
)
from energy_core.integrations.tesla.factory import build_tesla_provider, is_tesla_provider

__all__ = [
    "MercedesAuthError",
    "MercedesCommandFeatures",
    "build_charging_action_command",
    "build_mercedes_provider",
    "build_set_target_soc_command",
    "build_tesla_provider",
    "describe_client_message",
    "is_mercedes_provider",
    "is_tesla_provider",
    "wire_supervisor_token_callbacks",
]
