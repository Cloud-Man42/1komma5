"""Charging mode policy — priority and behaviour for Smart, Solar, Quick and override."""

from __future__ import annotations

SOLAR_MODES = frozenset({"SOLAR_CHARGE", "SOLAR"})
QUICK_MODES = frozenset({"QUICK_CHARGE", "QUICK"})
SMART_MODES = frozenset({"SMART_CHARGE", "SMART"})
PRICE_MODES = frozenset({"PRICE_CHARGE", "PRICE"})


def normalized_mode(charging_mode: str | None) -> str:
    return (charging_mode or "SMART_CHARGE").upper()


def decision_policy_mode(charging_mode: str | None, *, override_active: bool) -> str:
    if override_active:
        return "override"
    return normalized_mode(charging_mode)


def respects_manual_pause(charging_mode: str | None, *, override_active: bool) -> bool:
    """True when explicit PAUSED should block charging (override wins over pause)."""
    return normalized_mode(charging_mode) == "PAUSED" and not override_active


def immediate_start(charging_mode: str | None, *, override_active: bool) -> bool:
    """Quick charge and manual override start without anti-flap start delay."""
    if override_active:
        return True
    return normalized_mode(charging_mode) in QUICK_MODES


def uses_start_delay(charging_mode: str | None, *, override_active: bool) -> bool:
    """Smart and price modes use the general start delay; solar has its own in the optimizer."""
    if immediate_start(charging_mode, override_active=override_active):
        return False
    mode = normalized_mode(charging_mode)
    if mode in SOLAR_MODES:
        return False
    return mode in SMART_MODES | PRICE_MODES


def bypasses_guardrails(charging_mode: str | None, *, override_active: bool) -> bool:
    """Skip cooldown and hourly auto-start limits for user-initiated fast charging."""
    return immediate_start(charging_mode, override_active=override_active)


def uses_price_optimization(charging_mode: str | None, *, override_active: bool) -> bool:
    if override_active or normalized_mode(charging_mode) in QUICK_MODES:
        return False
    return normalized_mode(charging_mode) in SMART_MODES | PRICE_MODES


def ignores_schedule_constraints(charging_mode: str | None) -> bool:
    """True when departure, deadline and required energy must not affect charging."""
    return normalized_mode(charging_mode) in PRICE_MODES


def uses_solar_export_rules(charging_mode: str | None, *, override_active: bool) -> bool:
    if override_active or normalized_mode(charging_mode) in QUICK_MODES:
        return False
    return normalized_mode(charging_mode) in SOLAR_MODES | SMART_MODES
