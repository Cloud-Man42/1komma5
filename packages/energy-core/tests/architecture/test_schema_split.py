"""Architecture tests for split API schemas."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMAS_DIR = REPO_ROOT / "backend" / "app" / "schemas"


def test_schemas_package_has_domain_modules() -> None:
    expected = {
        "sites.py",
        "ev.py",
        "solar.py",
        "spa.py",
        "vehicles.py",
        "dashboard.py",
    }
    present = {path.name for path in SCHEMAS_DIR.glob("*.py") if path.name != "__init__.py"}
    assert expected.issubset(present)


def test_monolithic_schemas_module_removed() -> None:
    assert not (REPO_ROOT / "backend" / "app" / "schemas.py").exists()


def test_schema_package_exports_dashboard_and_spa() -> None:
    from app.schemas import DashboardResponse, SpaHealthResponse

    assert DashboardResponse.model_fields["site"].annotation is not None
    assert "health_status" in SpaHealthResponse.model_fields
