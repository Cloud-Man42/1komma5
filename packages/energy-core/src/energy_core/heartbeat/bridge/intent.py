"""Parse Heartbeat charging intent from EV profile, EMS and AI decisions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.heartbeat.discovery.models import HeartbeatIntent

EV_CHARGE_DECISIONS = frozenset(
    {
        "EV_CHARGE_FROM_GRID",
        "EV_CHARGE",
        "CHARGE_EV",
        "EV_SOLAR_CHARGE",
    }
)


def normalize_charging_mode(raw: str | None) -> str:
    if not raw:
        return "UNKNOWN"
    upper = raw.upper()
    if upper in {"SMART_CHARGE", "SOLAR_CHARGE", "QUICK_CHARGE", "PRICE_CHARGE", "PAUSED"}:
        return upper
    return f"UNKNOWN: {raw}"


class HeartbeatIntentParser:
    def parse(
        self,
        *,
        ev_profile: dict[str, Any] | None,
        ems_settings: dict[str, Any] | None,
        optimizations: list[dict[str, Any]] | None,
        confidence: float = 100.0,
    ) -> HeartbeatIntent:
        charge_settings = (ev_profile or {}).get("chargeSettings") or {}
        mode = normalize_charging_mode(charge_settings.get("chargingMode") or (ems_settings or {}).get("activeChargingMode"))
        target_soc = charge_settings.get("targetSoc")
        target_pct: float | None = None
        if target_soc is not None:
            try:
                target_pct = float(target_soc) * 100 if float(target_soc) <= 1 else float(target_soc)
            except (TypeError, ValueError):
                target_pct = None

        ai_reason: str | None = None
        raw_decision: str | None = None
        charge_requested = mode in {"SMART_CHARGE", "SOLAR_CHARGE", "QUICK_CHARGE", "PRICE_CHARGE"}
        preferred_source: str | None = None

        for item in optimizations or []:
            for key in ("decisionType", "type", "action"):
                value = item.get(key)
                if value:
                    raw_decision = str(value)
                    break
            if raw_decision:
                ai_reason = raw_decision
                if raw_decision in EV_CHARGE_DECISIONS or "EV" in raw_decision.upper():
                    charge_requested = True
                if "SOLAR" in raw_decision.upper():
                    preferred_source = "SOLAR"
                elif "GRID" in raw_decision.upper():
                    preferred_source = "GRID"
                break

        if mode == "SOLAR_CHARGE":
            preferred_source = "SOLAR"
        elif mode in {"SMART_CHARGE", "QUICK_CHARGE", "PRICE_CHARGE"}:
            preferred_source = preferred_source or "GRID"

        return HeartbeatIntent(
            charge_requested=charge_requested,
            preferred_source=preferred_source,
            charging_mode=mode,
            target_soc_pct=target_pct,
            departure_time=charge_settings.get("primaryScheduleDepartureTime"),
            ai_reason=ai_reason,
            valid_from=datetime.now(UTC),
            valid_until=None,
            confidence=confidence,
            raw_decision_type=raw_decision,
        )
