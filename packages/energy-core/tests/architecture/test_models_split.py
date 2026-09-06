"""Architecture tests for split ORM models."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MODELS_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "db" / "models"


def test_models_package_has_domain_modules() -> None:
    expected = {
        "base.py",
        "sites.py",
        "ev.py",
        "solar.py",
        "spa.py",
        "vehicles.py",
        "readings.py",
        "heartbeat.py",
    }
    present = {path.name for path in MODELS_DIR.glob("*.py") if path.name != "__init__.py"}
    assert expected.issubset(present)


def test_monolithic_models_module_removed() -> None:
    assert not (REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "db" / "models.py").exists()


def test_models_package_exports_site_and_ev_charger() -> None:
    from energy_core.db.models import Base, EvChargerModel, SiteModel

    assert SiteModel.__tablename__ == "sites"
    assert EvChargerModel.__tablename__ == "ev_chargers"
    assert "sites" in Base.metadata.tables
    assert "ev_chargers" in Base.metadata.tables


def test_alembic_metadata_includes_all_tables() -> None:
    from energy_core.db.models import Base

    assert len(Base.metadata.tables) >= 70
