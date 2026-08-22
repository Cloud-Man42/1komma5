"""Charging decision models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChargingDecision:
    requested_current_a: float
    applied_current_a: float
    requested_power_w: float | None
    action: str
    reason: str
    policy_mode: str
    skip_apply: bool = False
    smart_charging_state: str | None = None
    externally_limited: bool = False


@dataclass(frozen=True, slots=True)
class BridgeStatus:
    charger_id: int
    bridge_enabled: bool
    charging_mode: str
    active_policy: str
    ev_target_power_w: float | None
    requested_current_a: float | None
    applied_current_a: float | None
    previous_current_a: float | None
    configured_current_a: float | None = None
    actual_charging_current_a: float | None = None
    actual_power_w: float | None = None
    smart_charging_state: str | None = None
    externally_limited: bool = False
    display_status_sv: str | None = None
    fuse_headroom_a: float | None = None
    last_heartbeat_data_at: datetime | None = None
    last_bridge_run_at: datetime | None = None
    halo_connected: bool | None = None
    vehicle_connected: bool | None = None
    decision_reason: str | None = None
    discovery_hints: tuple[str, ...] = ()
    stale: bool = False
    override_active: bool = False
    override_until: datetime | None = None
    last_error_code: str | None = None
    last_charging_action: str | None = None
    phase_current_l1_a: float | None = None
    phase_current_l2_a: float | None = None
    phase_current_l3_a: float | None = None
