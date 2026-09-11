"""Tests for shared spa compute module and display layering."""

from __future__ import annotations

import ast
from pathlib import Path


def test_display_service_does_not_import_spa_api_routes():
    source = Path(__file__).resolve().parents[1] / "app" / "display_service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    spa_api_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "app.api.spa"
    ]
    assert spa_api_imports == []


def test_spa_api_reuses_spa_compute_helpers():
    from app.api import spa as spa_api
    from app.spa_compute import get_spa_context, spa_period_range

    assert spa_api._get_spa_context is get_spa_context
    assert spa_api._period_range is spa_period_range
