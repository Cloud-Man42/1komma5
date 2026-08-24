"""Parse and build Heartbeat EV charge setting payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

HEARTBEAT_CHARGING_MODES = frozenset({"SMART_CHARGE", "PRICE_CHARGE", "QUICK_CHARGE", "SOLAR_CHARGE"})
EMIC_ONLY_MODES = frozenset({"PAUSED"})


@dataclass(frozen=True, slots=True)
class HeartbeatEvSettings:
    charging_mode: str | None
    target_soc_pct: float | None
    departure_time: str | None
    remote_updated_at: datetime | None


def parse_ev_settings(ev: dict[str, Any] | None) -> HeartbeatEvSettings:
    if not ev:
        return HeartbeatEvSettings(
            charging_mode=None,
            target_soc_pct=None,
            departure_time=None,
            remote_updated_at=None,
        )
    settings = ev.get("chargeSettings") or {}
    target_soc = settings.get("targetSoc")
    return HeartbeatEvSettings(
        charging_mode=str(settings["chargingMode"]) if settings.get("chargingMode") else None,
        target_soc_pct=float(target_soc) * 100.0 if target_soc is not None else None,
        departure_time=settings.get("primaryScheduleDepartureTime"),
        remote_updated_at=_parse_timestamp(ev.get("updatedAt") or settings.get("chargingModeUpdatedAt")),
    )


def build_charge_settings_patch(
    *,
    charging_mode: str | None = None,
    target_soc_pct: float | None = None,
    departure_time: str | None = None,
) -> dict[str, Any]:
    charge_settings: dict[str, Any] = {}
    if charging_mode is not None:
        normalized = charging_mode.upper()
        if normalized in EMIC_ONLY_MODES:
            raise ValueError(f"Charging mode {charging_mode} cannot be written to Heartbeat")
        if normalized not in HEARTBEAT_CHARGING_MODES:
            raise ValueError(f"Unsupported Heartbeat charging mode: {charging_mode}")
        charge_settings["chargingMode"] = normalized
    if target_soc_pct is not None:
        charge_settings["targetSoc"] = max(0.0, min(1.0, float(target_soc_pct) / 100.0))
    if departure_time is not None:
        charge_settings["primaryScheduleDepartureTime"] = departure_time
    if not charge_settings:
        return {}
    return {"chargeSettings": charge_settings}


def settings_differ(local: HeartbeatEvSettings, remote: HeartbeatEvSettings) -> bool:
    return (
        _normalize_mode(local.charging_mode) != _normalize_mode(remote.charging_mode)
        or _normalize_soc(local.target_soc_pct) != _normalize_soc(remote.target_soc_pct)
        or (local.departure_time or "") != (remote.departure_time or "")
    )


def _normalize_mode(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.upper()
    if normalized in EMIC_ONLY_MODES:
        return None
    return normalized


def _normalize_soc(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 1)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
