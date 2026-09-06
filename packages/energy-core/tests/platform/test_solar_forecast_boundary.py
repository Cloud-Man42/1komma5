"""Tests for unified solar forecast platform boundary."""

from __future__ import annotations


def test_solar_forecast_api_read_shims_platform_read_path() -> None:
    from energy_core.platform.forecasting.read_path import resolve_forecast_for_read as platform_read
    from energy_core.solar_forecast.api_read import resolve_forecast_for_read as shim_read

    assert shim_read is platform_read


def test_backend_solar_routes_use_platform_forecasting_not_solar_intelligence() -> None:
    import ast
    from pathlib import Path

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


def test_collector_builds_solar_forecast_via_platform_factory() -> None:
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[4] / "collector" / "app" / "collector.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "energy_core.solar_forecast.coordinator" not in modules
    assert "energy_core.platform.forecasting" in modules
