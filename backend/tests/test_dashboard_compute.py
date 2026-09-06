"""Tests for shared dashboard compute module and layering."""

from __future__ import annotations

import ast
from pathlib import Path


def test_display_service_imports_dashboard_compute_not_api():
    source = Path(__file__).resolve().parents[1] / "app" / "display_service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    api_dashboard_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "app.api.dashboard"
    ]
    assert api_dashboard_imports == []


def test_dashboard_api_reexports_section_cache_for_tests():
    from app.api import dashboard as dashboard_api
    from app.dashboard_compute import _CACHE as compute_cache

    assert dashboard_api._CACHE is compute_cache


def test_stale_seconds_shared_between_api_and_compute():
    from app.api.dashboard import STALE_SECONDS as api_stale
    from app.dashboard_compute import STALE_SECONDS as compute_stale

    assert api_stale == compute_stale == 480
