"""Tests for energy control provider factory."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from energy_core.config import Settings
from energy_core.energy_control.chargeamps_provider import ChargeAmpsControlProvider
from energy_core.energy_control.heartbeat_provider import HeartbeatControlProvider
from energy_core.energy_control.provider_factory import resolve_control_provider


def test_resolve_control_provider_noop() -> None:
    settings = Settings(_env_file=None, ENERGY_CONTROL_PROVIDER="noop")
    provider = resolve_control_provider(settings)
    assert provider.provider_name == "noop-dry-run"


def test_resolve_control_provider_heartbeat_requires_session() -> None:
    settings = Settings(_env_file=None, ENERGY_CONTROL_PROVIDER="heartbeat")
    with pytest.raises(ValueError, match="requires database session"):
        resolve_control_provider(settings)


def test_resolve_control_provider_heartbeat() -> None:
    settings = Settings(_env_file=None, ENERGY_CONTROL_PROVIDER="heartbeat")
    provider = resolve_control_provider(settings, session=AsyncMock())
    assert isinstance(provider, HeartbeatControlProvider)
    assert provider.provider_name == "heartbeat"


def test_resolve_control_provider_chargeamps() -> None:
    settings = Settings(_env_file=None, ENERGY_CONTROL_PROVIDER="chargeamps")
    provider = resolve_control_provider(settings, session=AsyncMock())
    assert isinstance(provider, ChargeAmpsControlProvider)
    assert provider.provider_name == "chargeamps"


def test_resolve_control_provider_unknown_raises() -> None:
    settings = Settings(_env_file=None, ENERGY_CONTROL_PROVIDER="unknown-provider")
    with pytest.raises(ValueError, match="Unknown energy control provider"):
        resolve_control_provider(settings)
