"""Architecture tests for domain event wiring."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ENERGY_CORE_SRC = REPO_ROOT / "packages" / "energy-core" / "src" / "energy_core"


def test_event_publish_helpers_exist() -> None:
    publish_path = ENERGY_CORE_SRC / "platform" / "events" / "publish.py"
    assert publish_path.exists()
    text = publish_path.read_text(encoding="utf-8")
    assert "publish_charging_session_started" in text
    assert "publish_integration_health_changed" in text
    assert "publish_vehicle_state_changed" in text


def test_collector_registers_default_subscribers() -> None:
    collector_path = REPO_ROOT / "collector" / "app" / "collector.py"
    text = collector_path.read_text(encoding="utf-8")
    assert "register_default_subscribers" in text
    assert "get_event_bus" in text


def test_platform_event_singleton_available() -> None:
    from energy_core.platform.events.bus import get_event_bus, reset_event_bus

    reset_event_bus()
    bus_a = get_event_bus()
    bus_b = get_event_bus()
    assert bus_a is bus_b
    reset_event_bus()
