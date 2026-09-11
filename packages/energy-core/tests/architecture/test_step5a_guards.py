"""Step 5A architecture guards."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
LOADER = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core" / "platform" / "modules" / "packages" / "loader.py"

FORBIDDEN = (
    "integrations/chargeamps",
    "integrations/mercedes",
    "integrations/arctic_spa",
    "integrations/heartbeat",
)


def test_package_loader_avoids_direct_vendor_imports():
    text = LOADER.read_text(encoding="utf-8")
    violations = [needle for needle in FORBIDDEN if needle in text]
    assert not violations
