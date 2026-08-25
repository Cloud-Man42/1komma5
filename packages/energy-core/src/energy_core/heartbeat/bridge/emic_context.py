"""Correlate EMIC vehicle integration with Heartbeat EV discovery."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.vehicle_repo import VehicleRepository
from energy_core.heartbeat.discovery.models import HeartbeatEvDiscoveryResult
from energy_core.heartbeat.discovery.report import generate_discovery_report


async def enrich_discovery_with_emic_vehicles(
    session: AsyncSession,
    site_id: int,
    result: HeartbeatEvDiscoveryResult,
) -> HeartbeatEvDiscoveryResult:
    repo = VehicleRepository(session)
    vehicles = await repo.list_for_site(site_id)
    if not vehicles:
        return result

    emic_lines: list[str] = []
    for vehicle in vehicles:
        state = await repo.get_latest_state(vehicle.id)
        parts = [f"{vehicle.provider}: {vehicle.display_name} ({vehicle.manufacturer} {vehicle.model})"]
        if state is not None:
            parts.append(f"connection={state.connection_state or 'UNKNOWN'}")
            if state.state_of_charge_percent is not None:
                parts.append(f"SoC={state.state_of_charge_percent:.0f}%")
        emic_lines.append(" — ".join(parts))

    warnings = list(result.warnings)
    if not result.ev_profiles:
        warnings.append(
            "EMIC has registered vehicle(s) but Heartbeat returned 0 EV profiles. "
            "Register the same vehicle in the Heartbeat app to obtain an EV ID."
        )

    new_warnings = tuple(dict.fromkeys(warnings))
    interim = HeartbeatEvDiscoveryResult(
        site_slug=result.site_slug,
        site_name=result.site_name,
        system_id=result.system_id,
        authenticated=result.authenticated,
        ev_profiles=result.ev_profiles,
        wallboxes=result.wallboxes,
        ems_devices=result.ems_devices,
        assignments=result.assignments,
        charging_modes=result.charging_modes,
        ai_decision_types=result.ai_decision_types,
        ai_decisions_found=result.ai_decisions_found,
        resolved_ev_id=result.resolved_ev_id,
        setup_classification=result.setup_classification,
        bridge_lifecycle=result.bridge_lifecycle,
        halo_found=result.halo_found,
        halo_online=result.halo_online,
        virtual_bridge_suitable=result.virtual_bridge_suitable,
        warnings=new_warnings,
        observations=result.observations,
        field_hints=result.field_hints,
        started_at=result.started_at,
        completed_at=result.completed_at,
        emic_vehicle_lines=tuple(emic_lines),
    )
    report_text = generate_discovery_report(interim)
    return HeartbeatEvDiscoveryResult(
        site_slug=interim.site_slug,
        site_name=interim.site_name,
        system_id=interim.system_id,
        authenticated=interim.authenticated,
        ev_profiles=interim.ev_profiles,
        wallboxes=interim.wallboxes,
        ems_devices=interim.ems_devices,
        assignments=interim.assignments,
        charging_modes=interim.charging_modes,
        ai_decision_types=interim.ai_decision_types,
        ai_decisions_found=interim.ai_decisions_found,
        resolved_ev_id=interim.resolved_ev_id,
        setup_classification=interim.setup_classification,
        bridge_lifecycle=interim.bridge_lifecycle,
        halo_found=interim.halo_found,
        halo_online=interim.halo_online,
        virtual_bridge_suitable=interim.virtual_bridge_suitable,
        warnings=interim.warnings,
        observations=interim.observations,
        field_hints=interim.field_hints,
        started_at=interim.started_at,
        completed_at=interim.completed_at,
        report_text=report_text,
        emic_vehicle_lines=interim.emic_vehicle_lines,
    )
