"""Tests for unified solar forecast platform boundary."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_solar_forecast_api_read_shim_removed() -> None:
    repo = Path(__file__).resolve().parents[4]
    assert not (repo / "packages/energy-core/src/energy_core/solar_forecast/api_read.py").exists()


def test_build_active_forecast_coordinator_selects_stack() -> None:
    from unittest.mock import MagicMock

    from energy_core.platform.forecasting.factory import (
        build_active_forecast_coordinator,
        build_solar_forecast_coordinator,
        build_solar_intelligence_coordinator,
    )

    settings = MagicMock()
    classic = build_active_forecast_coordinator(settings, solar_intelligence_enabled=False)
    intelligent = build_active_forecast_coordinator(settings, solar_intelligence_enabled=True)
    assert type(classic) is type(build_solar_forecast_coordinator(settings))
    assert type(intelligent) is type(build_solar_intelligence_coordinator(settings))


def test_backend_solar_routes_use_platform_forecasting_not_solar_intelligence() -> None:
    import ast

    repo = Path(__file__).resolve().parents[4]
    for rel in (
        "backend/app/api/solar_forecast.py",
        "backend/app/api/solar_intelligence.py",
    ):
        source = repo / rel
        tree = ast.parse(source.read_text(encoding="utf-8"))
        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "energy_core.solar_intelligence.service" not in modules, rel
        assert "energy_core.solar_intelligence.geometry" not in modules, rel
        assert "energy_core.platform.forecasting" in modules, rel


def test_solar_site_config_issue_detects_disabled_and_incomplete() -> None:
    from energy_core.platform.forecasting.site_config import solar_site_config_issue

    disabled = solar_site_config_issue(SimpleNamespace(enabled=False))
    assert disabled is not None
    assert disabled.status_code == 404
    assert "inte aktiverad" in disabled.detail

    incomplete = solar_site_config_issue(
        SimpleNamespace(enabled=True, latitude=None, longitude=13.0, installed_peak_power_kw=8.0)
    )
    assert incomplete is not None
    assert "ofullständig" in incomplete.detail

    ok = solar_site_config_issue(
        SimpleNamespace(enabled=True, latitude=55.5, longitude=13.0, installed_peak_power_kw=8.0)
    )
    assert ok is None


def test_collector_builds_solar_forecast_via_platform_factory() -> None:
    import ast

    source = Path(__file__).resolve().parents[4] / "collector" / "app" / "collector.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "energy_core.solar_forecast.coordinator" not in modules
    assert "energy_core.platform.forecasting" in modules
