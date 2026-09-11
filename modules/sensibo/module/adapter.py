"""Normalize Sensibo vendor payloads to generic climate readings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_pod_reading(
    *,
    pod: dict[str, Any],
    measurement: dict[str, Any] | None,
    site_id: int,
) -> dict[str, Any]:
    pod_id = str(pod.get("id") or pod.get("deviceUid") or "")
    ac_state = pod.get("acState") if isinstance(pod.get("acState"), dict) else {}
    measurement = measurement or {}
    observed_at = (
        _parse_iso(measurement.get("time"))
        or _parse_iso(pod.get("measurementsUpdatedAt"))
        or datetime.now(UTC)
    )
    temperature_c = measurement.get("temperature")
    if temperature_c is None and isinstance(ac_state, dict):
        temperature_c = ac_state.get("targetTemperature") or ac_state.get("temperature")
    humidity = measurement.get("humidity")
    if humidity is None and isinstance(measurement.get("fields"), dict):
        humidity = measurement["fields"].get("humidity")
    mode = None
    if isinstance(ac_state, dict):
        mode = ac_state.get("mode") or ac_state.get("on") and "on" or "off"
    target = None
    if isinstance(ac_state, dict):
        target = ac_state.get("targetTemperature")
    connection_status = pod.get("connectionStatus") or pod.get("connection_status")
    if isinstance(connection_status, dict):
        online = connection_status.get("isAlive")
    else:
        online = connection_status == "Connected" if connection_status else pod.get("online")
    room = pod.get("room")
    if isinstance(room, dict):
        display_name = room.get("name") or pod.get("productModel") or pod_id
    else:
        display_name = room or pod.get("productModel") or pod_id
    return {
        "device_id": pod_id,
        "external_device_id": pod_id,
        "site_id": site_id,
        "display_name": str(display_name),
        "temperature_c": float(temperature_c) if temperature_c is not None else None,
        "humidity_percent": float(humidity) if humidity is not None else None,
        "climate_mode": str(mode) if mode is not None else None,
        "target_temperature_c": float(target) if target is not None else None,
        "online": bool(online) if online is not None else None,
        "source_quality": "LIVE",
        "observed_at": observed_at.isoformat(),
        "vendor": "Sensibo",
    }
