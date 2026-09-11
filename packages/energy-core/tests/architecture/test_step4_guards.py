"""Step 4 architecture guards."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULES_DEVICES_DIR = REPO_ROOT / "frontend" / "src" / "components" / "modules-devices"

FORBIDDEN_VENDOR_IMPORTS = (
    "integrations/chargeamps",
    "integrations/mercedes",
    "integrations/arctic_spa",
    "integrations/heartbeat",
)


def test_modules_devices_components_avoid_vendor_imports():
    if not MODULES_DEVICES_DIR.exists():
        return
    violations: list[str] = []
    for path in MODULES_DEVICES_DIR.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_VENDOR_IMPORTS:
            if needle in text:
                violations.append(f"{path.relative_to(REPO_ROOT)} imports {needle}")
    assert not violations, "\n".join(violations)


def test_module_config_get_masks_secrets_contract():
    from energy_core.platform.modules.config_schema import mask_config_for_response

    schema = {
        "fields": [
            {"name": "token", "label": "Token", "type": "secret", "secret": True},
            {"name": "host", "label": "Host", "type": "string"},
        ]
    }
    public, configured = mask_config_for_response(schema, {"token": "secret-value", "host": "x"})
    assert "token" not in public
    assert "secret-value" not in json.dumps(public)
    assert configured["token"] is True
