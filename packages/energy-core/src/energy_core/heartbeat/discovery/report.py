"""Generate discovery report text (§46 / §60 format)."""

from __future__ import annotations

from energy_core.heartbeat.discovery.models import HeartbeatEvDiscoveryResult, SetupClassification


def generate_discovery_report(
    result: HeartbeatEvDiscoveryResult,
    *,
    emic_vehicle_lines: tuple[str, ...] | None = None,
) -> str:
    emic_lines = emic_vehicle_lines if emic_vehicle_lines is not None else result.emic_vehicle_lines
    lines = [
        "=" * 40,
        "EMIC HEARTBEAT EV DISCOVERY RESULT",
        "=" * 40,
        "",
        f"Site: {result.site_name} ({result.site_slug})",
        "",
        f"Heartbeat authentication: {'PASS' if result.authenticated else 'FAIL'}",
        f"System ID: {result.system_id or 'NOT SET'}",
        "",
        f"EV profiles found: {len(result.ev_profiles)}",
    ]

    for profile in result.ev_profiles:
        lines.extend(
            [
                "",
                f"EV: {profile.manufacturer} {profile.model}".strip(),
                f"EV ID: {profile.heartbeat_ev_id}",
                f"Name: {profile.name}",
                f"Battery capacity: {profile.battery_capacity_kwh or 'unknown'} kWh",
                f"Current SoC: {profile.current_soc_pct if profile.current_soc_pct is not None else 'unknown'} %",
                f"Target SoC: {profile.target_soc_pct if profile.target_soc_pct is not None else 'unknown'} %",
                f"Charging mode: {profile.charging_mode or 'unknown'}",
                f"Assigned Charger: {profile.assigned_charger_id or 'NONE'}",
            ]
        )

    lines.extend(
        [
            "",
            "Physical Wallbox",
            f"Status: {'FOUND' if result.wallboxes else 'NOT FOUND'}",
        ]
    )
    for box in result.wallboxes:
        lines.extend(
            [
                f"  gridxHardwareId: {box.gridx_hardware_id or 'unknown'}",
                f"  assignedEvId: {box.assigned_ev_id or 'NONE'}",
                f"  name: {box.name}",
            ]
        )

    if emic_lines:
        lines.extend(["", "EMIC vehicle integration:"])
        for line in emic_lines:
            lines.append(f"  - {line}")

    lines.extend(
        [
            "",
            f"EMS EV devices: {sum(1 for d in result.ems_devices if d.ev_related)} EV-related / {len(result.ems_devices)} total",
            f"Heartbeat charging modes: {', '.join(result.charging_modes) or 'none observed'}",
            f"Heartbeat AI EV decisions: {'FOUND' if result.ai_decisions_found else 'NOT FOUND'}",
            f"Observed decision types: {', '.join(result.ai_decision_types) or 'none'}",
            "",
            f"Resolved EV ID: {result.resolved_ev_id.heartbeat_ev_id or 'NONE'}",
            f"EV-ID confidence: {result.resolved_ev_id.confidence_pct:.0f} %",
            f"Source: {result.resolved_ev_id.source}",
            "",
            f"Charge Amps Halo: {'FOUND' if result.halo_found else 'NOT FOUND'}",
            f"Halo online: {'YES' if result.halo_online else 'NO'}",
            f"Setup classification: {result.setup_classification.value} ({result.setup_classification.name})",
            f"Bridge lifecycle: {result.bridge_lifecycle.value}",
            f"Virtual Bridge suitability: {'YES' if result.virtual_bridge_suitable else 'NO'}",
        ]
    )

    if result.warnings:
        lines.extend(["", "Warnings:"])
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    lines.extend(["", "=" * 40, "CONCLUSION", "=" * 40, ""])
    lines.append(_conclusion_text(result))
    lines.extend(["", "=" * 40, "NEXT RECOMMENDED STEP", "=" * 40, ""])
    lines.append(_next_step(result))
    return "\n".join(lines)


def _conclusion_text(result: HeartbeatEvDiscoveryResult) -> str:
    if result.setup_classification == SetupClassification.HEARTBEAT_AUTH_FAILED:
        return "Heartbeat authentication failed. Check credentials in /config."
    if result.setup_classification == SetupClassification.EV_ID_NOT_FOUND:
        return (
            "No usable EV profile was found in Heartbeat for this site. "
            "Register the vehicle in the Heartbeat app, then re-run discovery."
        )
    if result.setup_classification == SetupClassification.VIRTUAL_CHARGER_BRIDGE_READY:
        return (
            "The current installation appears suitable for an EMIC Virtual Charger Bridge. "
            "Heartbeat has an EV profile but no native Heartbeat wallbox assignment is required."
        )
    if result.setup_classification == SetupClassification.FULL_NATIVE_HEARTBEAT_EV:
        return "Native Heartbeat EV + wallbox setup detected. Bridge can still orchestrate via Halo."
    if result.setup_classification == SetupClassification.HEARTBEAT_EV_WITHOUT_WALLBOX:
        return "EV profile exists without a matching Heartbeat wallbox — virtual bridge candidate."
    if result.setup_classification == SetupClassification.AMBIGUOUS_EV_MAPPING:
        return "Multiple or weak EV mappings detected. Manual review required before enabling bridge."
    return "Discovery completed. Review raw observations for details."


def _next_step(result: HeartbeatEvDiscoveryResult) -> str:
    if not result.authenticated:
        return "Fix Heartbeat credentials and re-run discovery."
    if result.setup_classification in {
        SetupClassification.VIRTUAL_CHARGER_BRIDGE_READY,
        SetupClassification.HEARTBEAT_EV_WITHOUT_WALLBOX,
    }:
        return "Run safe Heartbeat write test, then enable simulation mode."
    if result.resolved_ev_id.confidence_pct >= 90:
        return "Confirm EV mapping and run simulation mode before physical control."
    if result.setup_classification == SetupClassification.EV_ID_NOT_FOUND:
        return (
            "1. Add Mercedes EQE 500 (or your EV) in the Heartbeat app\n"
            "2. Re-run RUN HEARTBEAT EV DISCOVERY\n"
            "3. If class C appears: run write test (dry-run), then simulation/replay"
        )
    return "Resolve EV mapping ambiguity, then re-run discovery."
