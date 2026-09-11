"""Step 5C.1 / 5C.2 architecture guards."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MARKETPLACE_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "platform" / "modules" / "marketplace"
GOVERNANCE_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "platform" / "modules" / "governance"
FRONTEND_STORE = REPO_ROOT / "frontend" / "src" / "app" / "config" / "modules-devices" / "store"
FRONTEND_GOVERNANCE = REPO_ROOT / "frontend" / "src" / "components" / "modules-devices" / "governance"
DISTRIBUTION_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "platform" / "modules" / "distribution"
SUPPLY_CHAIN_DIR = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "platform" / "modules" / "supply_chain"


def test_marketplace_metadata_must_not_import_package_installer():
    for path in MARKETPLACE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "PackageInstaller" not in text
        assert "PackageUpdater" not in text
        assert "PackageRemover" not in text


def test_marketplace_metadata_must_not_import_orchestrator():
    forbidden = ("ModuleOrchestrator", "load_installed_module_packages")
    for path in MARKETPLACE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text


def test_no_public_store_browse_route():
    public_catalog = FRONTEND_STORE / "public"
    assert not public_catalog.exists()


def test_governance_must_not_import_package_installer():
    forbidden = ("PackageInstaller", "PackageUpdater", "PackageRemover", "ModuleOrchestrator", "DeviceControlBroker")
    for path in GOVERNANCE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not import {token}"


def test_policy_engine_must_not_import_marketplace_http_client():
    text = (GOVERNANCE_DIR / "policy_engine.py").read_text(encoding="utf-8")
    assert "MarketplaceHttpClient" not in text
    assert "httpx" not in text


def test_frontend_governance_must_not_embed_policy_logic():
    if not FRONTEND_GOVERNANCE.exists():
        return
    forbidden_tokens = ("ModuleInstallPolicyEngine", "PolicyReasonCode", "DEFAULT_DENY", "break_glass_active")
    for path in FRONTEND_GOVERNANCE.glob("*.tsx"):
        if path.name.endswith(".test.tsx"):
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in text, f"{path.name} must display API results only, not embed {token}"


def test_distribution_must_not_import_installer_or_orchestrator():
    forbidden = ("PackageInstaller", "PackageUpdater", "ModuleOrchestrator", "load_installed_module_packages", "importlib", "subprocess")
    for path in DISTRIBUTION_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not reference {token}"


def test_supply_chain_must_not_import_installer():
    forbidden = ("PackageInstaller", "ModuleOrchestrator", "load_installed_module_packages")
    for path in SUPPLY_CHAIN_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not reference {token}"
