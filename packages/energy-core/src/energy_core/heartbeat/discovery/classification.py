"""Setup classification A–G for Heartbeat Virtual EV Bridge."""

from __future__ import annotations

from energy_core.heartbeat.discovery.models import (
    BridgeLifecycleState,
    EvProfileDiscovery,
    ResolvedEvId,
    SetupClassification,
    WallboxDiscovery,
)


def classify_setup(
    *,
    authenticated: bool,
    ev_profiles: tuple[EvProfileDiscovery, ...],
    wallboxes: tuple[WallboxDiscovery, ...],
    resolved: ResolvedEvId,
    halo_found: bool,
) -> tuple[SetupClassification, BridgeLifecycleState, bool]:
    if not authenticated:
        return SetupClassification.HEARTBEAT_AUTH_FAILED, BridgeLifecycleState.DISABLED, False

    if not ev_profiles or resolved.heartbeat_ev_id is None:
        return SetupClassification.EV_ID_NOT_FOUND, BridgeLifecycleState.DISCOVERY, False

    if resolved.confidence_pct < 60:
        return SetupClassification.AMBIGUOUS_EV_MAPPING, BridgeLifecycleState.DISCOVERY, False

    has_wallbox = len(wallboxes) > 0
    ev_has_assignment = any(
        w.assigned_ev_id == resolved.heartbeat_ev_id for w in wallboxes if w.assigned_ev_id
    )

    if has_wallbox and ev_has_assignment:
        return (
            SetupClassification.FULL_NATIVE_HEARTBEAT_EV,
            BridgeLifecycleState.READY,
            halo_found,
        )

    if ev_profiles and not has_wallbox:
        return (
            SetupClassification.VIRTUAL_CHARGER_BRIDGE_READY,
            BridgeLifecycleState.VIRTUAL_CHARGER_BRIDGE_CANDIDATE,
            halo_found,
        )

    if ev_profiles and has_wallbox and not ev_has_assignment:
        return (
            SetupClassification.HEARTBEAT_EV_WITHOUT_WALLBOX,
            BridgeLifecycleState.VIRTUAL_CHARGER_BRIDGE_CANDIDATE,
            halo_found,
        )

    if resolved.confidence_pct >= 85 and halo_found:
        return (
            SetupClassification.VIRTUAL_CHARGER_BRIDGE_READY,
            BridgeLifecycleState.VIRTUAL_CHARGER_BRIDGE_CANDIDATE,
            True,
        )

    return SetupClassification.AMBIGUOUS_EV_MAPPING, BridgeLifecycleState.DISCOVERY, halo_found
