"""Heartbeat EV Discovery service — read-only diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.heartbeat.discovery.classification import classify_setup
from energy_core.heartbeat.discovery.confidence import resolve_best_ev_id
from energy_core.heartbeat.discovery.models import (
    EvAssignmentDiscovery,
    EvProfileDiscovery,
    EmsDeviceDiscovery,
    HeartbeatEvDiscoveryResult,
    WallboxDiscovery,
)
from energy_core.heartbeat.discovery.observing_client import ObservingHeartbeatClient
from energy_core.heartbeat.discovery.report import generate_discovery_report
from energy_core.heartbeat.field_discovery import discover_relevant_fields
from energy_core.heartbeat_client import HeartbeatClient, map_ev_live_state

KNOWN_MODES = frozenset({"SMART_CHARGE", "SOLAR_CHARGE", "QUICK_CHARGE", "PRICE_CHARGE", "PAUSED"})


def _parse_ev_profile(ev: dict[str, Any]) -> EvProfileDiscovery:
    profile = ev.get("profile") or {}
    charge_settings = ev.get("chargeSettings") or {}
    target_soc = charge_settings.get("targetSoc")
    manual_soc = ev.get("manualSoc")
    battery = profile.get("batteryCapacity") or profile.get("batteryCapacityKwh")
    battery_kwh: float | None = None
    if battery is not None:
        try:
            battery_kwh = float(battery)
        except (TypeError, ValueError):
            battery_kwh = None
    current_soc: float | None = None
    if manual_soc is not None:
        try:
            current_soc = float(manual_soc) * 100 if float(manual_soc) <= 1 else float(manual_soc)
        except (TypeError, ValueError):
            current_soc = None
    target_pct: float | None = None
    if target_soc is not None:
        try:
            target_pct = float(target_soc) * 100 if float(target_soc) <= 1 else float(target_soc)
        except (TypeError, ValueError):
            target_pct = None
    live = map_ev_live_state(ev)
    return EvProfileDiscovery(
        heartbeat_ev_id=str(ev.get("id", "")),
        name=str(profile.get("name") or live.name or "EV"),
        manufacturer=str(profile.get("manufacturer") or live.manufacturer or ""),
        model=str(profile.get("model") or live.model or ""),
        battery_capacity_kwh=battery_kwh,
        current_soc_pct=current_soc,
        target_soc_pct=target_pct,
        charging_mode=charge_settings.get("chargingMode") or live.charging_mode,
        departure_time=charge_settings.get("primaryScheduleDepartureTime") or live.departure_time,
        assigned_charger_id=str(ev.get("assignedChargerId") or live.heartbeat_charger_id or "") or None,
        raw=ev,
    )


def _parse_wallbox(box: dict[str, Any]) -> WallboxDiscovery:
    return WallboxDiscovery(
        heartbeat_charger_id=str(box.get("id") or box.get("gridxHardwareId") or ""),
        gridx_hardware_id=str(box.get("gridxHardwareId") or "") or None,
        name=str(box.get("name") or "Wallbox"),
        manufacturer=str(box.get("manufacturer") or ""),
        model=str(box.get("model") or ""),
        assigned_ev_id=str(box.get("assignedEvId") or "") or None,
        status=str(box.get("status") or "") or None,
        raw=box,
    )


def _parse_ems_devices(ems: dict[str, Any]) -> tuple[EmsDeviceDiscovery, ...]:
    devices: list[EmsDeviceDiscovery] = []
    for key in ("devices", "emsDevices", "connectedDevices"):
        items = ems.get(key)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                dtype = str(item.get("type") or item.get("deviceType") or "unknown")
                label = str(item.get("name") or item.get("label") or item.get("id") or "")
                ev_related = "ev" in dtype.lower() or "charger" in dtype.lower() or "vehicle" in label.lower()
                devices.append(
                    EmsDeviceDiscovery(
                        device_id=str(item.get("id") or label),
                        device_type=dtype,
                        label=label,
                        ev_related=ev_related,
                        raw=item,
                    )
                )
    if not devices and ems:
        active = ems.get("activeChargingMode")
        if active:
            devices.append(
                EmsDeviceDiscovery(
                    device_id="ems",
                    device_type="ems_settings",
                    label=str(active),
                    ev_related=True,
                    raw=ems,
                )
            )
    return tuple(devices)


def _extract_ai_decision_types(optimizations: list[dict[str, Any]]) -> tuple[str, ...]:
    types: list[str] = []
    for item in optimizations:
        for key in ("decisionType", "type", "action", "optimizationType"):
            value = item.get(key)
            if value:
                types.append(str(value))
        nested = item.get("decision") or item.get("optimization")
        if isinstance(nested, dict):
            for key in ("decisionType", "type"):
                value = nested.get(key)
                if value:
                    types.append(str(value))
    return tuple(dict.fromkeys(types))


def _normalize_charging_modes(raw: Any) -> tuple[str, ...]:
    modes: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                modes.append(item if item in KNOWN_MODES else f"UNKNOWN: {item}")
            elif isinstance(item, dict):
                mode = item.get("mode") or item.get("chargingMode") or item.get("type") or item.get("id")
                if mode:
                    mode_str = str(mode)
                    modes.append(mode_str if mode_str in KNOWN_MODES else f"UNKNOWN: {mode_str}")
    return tuple(dict.fromkeys(modes))


def _build_assignments(
    profiles: tuple[EvProfileDiscovery, ...],
    wallboxes: tuple[WallboxDiscovery, ...],
) -> tuple[EvAssignmentDiscovery, ...]:
    wallbox_by_ev = {w.assigned_ev_id: w for w in wallboxes if w.assigned_ev_id}
    result: list[EvAssignmentDiscovery] = []
    for profile in profiles:
        wallbox = wallbox_by_ev.get(profile.heartbeat_ev_id)
        charger_id = wallbox.heartbeat_charger_id if wallbox else profile.assigned_charger_id
        result.append(
            EvAssignmentDiscovery(
                ev_id=profile.heartbeat_ev_id,
                charger_id=charger_id,
                source="assignedEvId" if wallbox else "ev_profile_only",
                matched=wallbox is not None,
            )
        )
    return tuple(result)


class HeartbeatEvDiscoveryService:
    """Read-only Heartbeat EV / wallbox / EMS discovery."""

    async def run(
        self,
        *,
        client: HeartbeatClient,
        site_slug: str,
        site_name: str,
        system_id: str | None,
        halo_found: bool = False,
        halo_online: bool = False,
    ) -> HeartbeatEvDiscoveryResult:
        started = datetime.now(UTC)
        warnings: list[str] = []
        authenticated = client is not None

        if client is None:
            completed = datetime.now(UTC)
            resolved = resolve_best_ev_id((), (), ())
            classification, lifecycle, suitable = classify_setup(
                authenticated=False,
                ev_profiles=(),
                wallboxes=(),
                resolved=resolved,
                halo_found=halo_found,
            )
            result = HeartbeatEvDiscoveryResult(
                site_slug=site_slug,
                site_name=site_name,
                system_id=system_id,
                authenticated=False,
                ev_profiles=(),
                wallboxes=(),
                ems_devices=(),
                assignments=(),
                charging_modes=(),
                ai_decision_types=(),
                ai_decisions_found=False,
                resolved_ev_id=resolved,
                setup_classification=classification,
                bridge_lifecycle=lifecycle,
                halo_found=halo_found,
                halo_online=halo_online,
                virtual_bridge_suitable=suitable,
                warnings=("Heartbeat client not available — check connection config",),
                observations=(),
                field_hints=(),
                started_at=started,
                completed_at=completed,
            )
            return _with_report(result)

        if not system_id:
            completed = datetime.now(UTC)
            resolved = resolve_best_ev_id((), (), ())
            classification, lifecycle, suitable = classify_setup(
                authenticated=authenticated,
                ev_profiles=(),
                wallboxes=(),
                resolved=resolved,
                halo_found=halo_found,
            )
            result = HeartbeatEvDiscoveryResult(
                site_slug=site_slug,
                site_name=site_name,
                system_id=None,
                authenticated=authenticated,
                ev_profiles=(),
                wallboxes=(),
                ems_devices=(),
                assignments=(),
                charging_modes=(),
                ai_decision_types=(),
                ai_decisions_found=False,
                resolved_ev_id=resolved,
                setup_classification=classification,
                bridge_lifecycle=lifecycle,
                halo_found=halo_found,
                halo_online=halo_online,
                virtual_bridge_suitable=suitable,
                warnings=("Site has no Heartbeat system ID configured",),
                observations=(),
                field_hints=(),
                started_at=started,
                completed_at=completed,
            )
            return _with_report(result)

        observer = ObservingHeartbeatClient(client)
        ev_profiles: tuple[EvProfileDiscovery, ...] = ()
        wallboxes: tuple[WallboxDiscovery, ...] = ()
        ems_devices: tuple[EmsDeviceDiscovery, ...] = ()
        charging_modes: tuple[str, ...] = ()
        ai_types: tuple[str, ...] = ()
        ai_found = False
        field_hints: tuple[str, ...] = ()

        try:
            ev_raw = await observer.list_evs(system_id)
            ev_profiles = tuple(_parse_ev_profile(ev) for ev in ev_raw if ev.get("id"))
        except Exception as exc:
            warnings.append(f"EV list failed: {exc}")

        try:
            box_raw = await observer.list_wallboxes(system_id)
            wallboxes = tuple(_parse_wallbox(box) for box in box_raw if box.get("id") or box.get("gridxHardwareId"))
        except Exception as exc:
            warnings.append(f"Wallbox list failed: {exc}")

        try:
            ems_raw = await observer.fetch_ems_settings(system_id)
            ems_devices = _parse_ems_devices(ems_raw)
            field_hints = tuple(dict.fromkeys(field_hints + discover_relevant_fields(ems_raw)))
        except Exception as exc:
            warnings.append(f"EMS settings failed: {exc}")

        try:
            modes_raw = await observer.list_charging_modes(system_id)
            charging_modes = _normalize_charging_modes(modes_raw)
        except Exception:
            for profile in ev_profiles:
                if profile.charging_mode:
                    mode = profile.charging_mode
                    charging_modes = charging_modes + (
                        mode if mode in KNOWN_MODES else f"UNKNOWN: {mode}",
                    )
            charging_modes = tuple(dict.fromkeys(charging_modes))

        try:
            now = datetime.now(UTC)
            opts = await observer.fetch_optimizations(
                system_id,
                from_iso=(now - timedelta(hours=24)).isoformat(),
                to_iso=now.isoformat(),
            )
            ai_types = _extract_ai_decision_types(opts)
            ai_found = len(ai_types) > 0
        except Exception as exc:
            warnings.append(f"AI optimizations failed: {exc}")

        try:
            overview = await observer.fetch_live_overview(system_id)
            field_hints = tuple(dict.fromkeys(field_hints + discover_relevant_fields(overview)))
        except Exception as exc:
            warnings.append(f"Live overview failed: {exc}")

        assignments = _build_assignments(ev_profiles, wallboxes)
        resolved = resolve_best_ev_id(ev_profiles, assignments, wallboxes)
        warnings.extend(resolved.warnings)

        classification, lifecycle, suitable = classify_setup(
            authenticated=True,
            ev_profiles=ev_profiles,
            wallboxes=wallboxes,
            resolved=resolved,
            halo_found=halo_found,
        )

        completed = datetime.now(UTC)
        result = HeartbeatEvDiscoveryResult(
            site_slug=site_slug,
            site_name=site_name,
            system_id=system_id,
            authenticated=True,
            ev_profiles=ev_profiles,
            wallboxes=wallboxes,
            ems_devices=ems_devices,
            assignments=assignments,
            charging_modes=charging_modes,
            ai_decision_types=ai_types,
            ai_decisions_found=ai_found,
            resolved_ev_id=resolved,
            setup_classification=classification,
            bridge_lifecycle=lifecycle,
            halo_found=halo_found,
            halo_online=halo_online,
            virtual_bridge_suitable=suitable,
            warnings=tuple(dict.fromkeys(warnings)),
            observations=tuple(observer.observations),
            field_hints=field_hints,
            started_at=started,
            completed_at=completed,
        )
        return _with_report(result)


def _with_report(result: HeartbeatEvDiscoveryResult) -> HeartbeatEvDiscoveryResult:
    report = generate_discovery_report(result)
    return HeartbeatEvDiscoveryResult(
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
        warnings=result.warnings,
        observations=result.observations,
        field_hints=result.field_hints,
        started_at=result.started_at,
        completed_at=result.completed_at,
        report_text=report,
        emic_vehicle_lines=result.emic_vehicle_lines,
    )
