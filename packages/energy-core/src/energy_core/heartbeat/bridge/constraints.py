"""Resolve bridge constraints before Halo execution."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.heartbeat.discovery.models import HeartbeatIntent, HaloCommand


@dataclass(frozen=True, slots=True)
class BridgeConstraints:
    heartbeat_requested_power_w: float
    solar_available_power_w: float
    smart_charging_allowed_power_w: float
    load_balancer_allowed_power_w: float
    halo_hardware_limit_w: float
    vehicle_limit_w: float
    site_limit_w: float


@dataclass(frozen=True, slots=True)
class ResolvedBridgePower:
    allowed_power_w: float
    limiting_factor: str
    blocked: bool
    reason: str


class BridgeConstraintResolver:
    def resolve(
        self,
        intent: HeartbeatIntent,
        constraints: BridgeConstraints,
        *,
        min_power_w: float = 1400.0,
        battery_priority_mode: str = "BATTERY_FIRST",
    ) -> ResolvedBridgePower:
        if not intent.charge_requested:
            return ResolvedBridgePower(0.0, "heartbeat_not_requesting", True, "Heartbeat did not request charging")

        candidates = {
            "heartbeat": constraints.heartbeat_requested_power_w,
            "solar": constraints.solar_available_power_w,
            "smart_charging": constraints.smart_charging_allowed_power_w,
            "load_balancer": constraints.load_balancer_allowed_power_w,
            "halo_hardware": constraints.halo_hardware_limit_w,
            "vehicle": constraints.vehicle_limit_w,
            "site": constraints.site_limit_w,
        }

        if intent.preferred_source == "SOLAR" and battery_priority_mode == "BATTERY_FIRST":
            candidates["solar"] = min(candidates["solar"], candidates["smart_charging"])

        allowed = min(candidates.values())
        limiting = min(candidates, key=candidates.get)  # type: ignore[arg-type]

        if allowed < min_power_w:
            return ResolvedBridgePower(
                allowed,
                limiting,
                True,
                f"Allowed power {allowed:.0f} W below minimum {min_power_w:.0f} W ({limiting})",
            )

        return ResolvedBridgePower(allowed, limiting, False, f"Allowed {allowed:.0f} W limited by {limiting}")


def intent_to_halo_command(
    intent: HeartbeatIntent,
    resolved: ResolvedBridgePower,
    *,
    nominal_voltage_v: float = 230.0,
    phases: int = 3,
) -> HaloCommand:
    if resolved.blocked or resolved.allowed_power_w <= 0:
        return HaloCommand(action="stop", current_a=0.0, reason=resolved.reason)

    power = resolved.allowed_power_w
    current = power / (nominal_voltage_v * phases)
    if intent.charging_mode == "PAUSED" or intent.charging_mode.startswith("UNKNOWN"):
        return HaloCommand(action="pause", current_a=0.0, reason=f"Mode {intent.charging_mode}")

    return HaloCommand(
        action="set_current",
        current_a=round(max(6.0, current), 1),
        reason=resolved.reason,
    )
