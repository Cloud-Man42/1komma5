"""Tests for Arctic Spa integration boundary modules."""

from __future__ import annotations


def test_arctic_spa_control_service_implements_contract() -> None:
    from energy_core.contracts.spa.control import ISpaControlService
    from energy_core.integrations.arctic_spa.control_service import ArcticSpaControlService

    assert issubclass(ArcticSpaControlService, object)
    assert hasattr(ArcticSpaControlService, "get_status")


def test_spa_energy_routes_through_factory_not_control_service_module() -> None:
    import ast
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    for rel in (
        "packages/energy-core/src/energy_core/spa_energy/service.py",
        "packages/energy-core/src/energy_core/spa_energy/actuator.py",
        "packages/energy-core/src/energy_core/spa_energy/watchdog.py",
        "packages/energy-core/src/energy_core/spa_energy/filter_schedule_service.py",
    ):
        source = repo / rel
        tree = ast.parse(source.read_text(encoding="utf-8"))
        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "energy_core.integrations.arctic_spa.control_service" not in modules, rel
        assert "energy_core.integrations.arctic_spa.client" not in modules, rel


def test_collector_imports_arctic_spa_factory_not_polling_module() -> None:
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[4] / "collector" / "app" / "collector.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "energy_core.integrations.arctic_spa.polling" not in modules
    assert "energy_core.integrations.arctic_spa.factory" in modules
