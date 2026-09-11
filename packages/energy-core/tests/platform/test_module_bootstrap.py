"""Tests for module registry bootstrap."""

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.registry import default_module_registry


def test_register_default_modules_is_idempotent():
    default_module_registry.clear()
    register_default_modules()
    first = default_module_registry.list_modules()
    register_default_modules()
    second = default_module_registry.list_modules()
    assert len(first) >= 10
    assert first == second
    assert any(module.module_id == "feature.smart-charging" for module in first)
    assert any(module.module_id == "charging" for module in first)
