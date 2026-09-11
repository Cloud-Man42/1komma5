"""Step 5C.5 runtime isolation architecture guards."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SDK_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "emic_runtime_sdk"
BOOTSTRAP = REPO_ROOT / "scripts" / "isolated_runtime_bootstrap.py"
ISOLATION_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "platform" / "modules" / "isolation"


def test_runtime_sdk_must_not_import_energy_core():
    for path in SDK_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "energy_core" not in text
        assert "backend.app" not in text
        assert "sqlalchemy" not in text.lower()


def test_bootstrap_must_not_import_energy_core():
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "energy_core" not in text
    assert "backend.app" not in text


def test_isolation_must_not_import_package_installer():
    forbidden = ("PackageInstaller", "ModuleOrchestrator", "load_installed_module_packages")
    for path in ISOLATION_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not reference {token}"
