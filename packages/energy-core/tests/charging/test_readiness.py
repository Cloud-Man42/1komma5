"""Tests for Charge Amps config and charging readiness."""

import os

import pytest

from energy_core.chargers.chargeamps_config import (
    assert_chargeamps_production_safe,
    build_chargeamps_connection_info,
)
from energy_core.charging.readiness import evaluate_charging_readiness
from energy_core.db.models import EvChargerModel, SiteModel


def test_chargeamps_config_ready_when_credentials_present(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.setenv("CHARGEAMPS_API_KEY", "secret-key")

    info = build_chargeamps_connection_info()
    assert info.ready is True
    assert info.mock is False
    assert info.api_key_configured is True


def test_chargeamps_config_ready_for_web_provider(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_PROVIDER", "web")
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.delenv("CHARGEAMPS_API_KEY", raising=False)
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "pass")

    info = build_chargeamps_connection_info()
    assert info.ready is True
    assert info.provider == "web"
    assert info.effective_provider == "web"


def test_chargeamps_config_uses_per_charger_api_key(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_PROVIDER", "web")
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.delenv("CHARGEAMPS_API_KEY", raising=False)
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "pass")

    info = build_chargeamps_connection_info(charger_api_keys_configured=1)
    assert info.api_key_configured is True
    assert info.env_api_key_configured is False
    assert info.charger_api_keys_configured == 1
    assert info.effective_provider == "external"
    assert info.ready is True
    assert any("Per-laddbox API-nyckel" in note for note in info.notes)


def test_chargeamps_config_not_ready_in_mock_mode(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_MOCK", "true")
    monkeypatch.setenv("CHARGEAMPS_API_KEY", "secret-key")

    info = build_chargeamps_connection_info()
    assert info.ready is False
    assert "CHARGEAMPS_MOCK" in info.notes[0]


def test_production_guard_rejects_mock(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_MOCK", "true")
    with pytest.raises(RuntimeError, match="CHARGEAMPS_MOCK"):
        assert_chargeamps_production_safe(app_env="production")


def test_readiness_reports_missing_charger_id(monkeypatch):
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.setenv("CHARGEAMPS_PROVIDER", "web")
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "pass")

    site = SiteModel(id=1, slug="akarp", name="Åkarp", timezone="Europe/Stockholm", external_system_id="sys-1")
    charger = EvChargerModel(
        id=7,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        bridge_enabled=True,
        chargeamp_charger_id=None,
    )

    report = evaluate_charging_readiness([(charger, site)])
    assert report.active_bridge_chargers == 1
    assert report.ready is False
    assert any(issue.code == "missing_chargeamp_id" for issue in report.issues)
