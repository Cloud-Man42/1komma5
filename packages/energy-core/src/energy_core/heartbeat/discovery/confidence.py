"""EV-ID resolution and confidence scoring."""

from __future__ import annotations

import re

from energy_core.heartbeat.discovery.models import EvProfileDiscovery, EvAssignmentDiscovery, ResolvedEvId, WallboxDiscovery

MERCEDES_PATTERN = re.compile(r"mercedes", re.IGNORECASE)
EQE_PATTERN = re.compile(r"eqe", re.IGNORECASE)


def _matches_mercedes_eqe(profile: EvProfileDiscovery) -> bool:
    manufacturer = profile.manufacturer or ""
    model = profile.model or profile.name or ""
    return bool(MERCEDES_PATTERN.search(manufacturer) and EQE_PATTERN.search(model))


def resolve_best_ev_id(
    profiles: tuple[EvProfileDiscovery, ...],
    assignments: tuple[EvAssignmentDiscovery, ...],
    wallboxes: tuple[WallboxDiscovery, ...],
) -> ResolvedEvId:
    warnings: list[str] = []
    if not profiles:
        return ResolvedEvId(
            heartbeat_ev_id=None,
            confidence_pct=0.0,
            source="none",
            ev_name=None,
            warnings=("No EV profiles found in Heartbeat",),
        )

    assignment_by_ev = {a.ev_id: a for a in assignments if a.ev_id}
    mercedes_matches = [p for p in profiles if _matches_mercedes_eqe(p)]

    if len(profiles) == 1:
        profile = profiles[0]
        assignment = assignment_by_ev.get(profile.heartbeat_ev_id)
        if assignment and assignment.matched:
            return ResolvedEvId(
                heartbeat_ev_id=profile.heartbeat_ev_id,
                confidence_pct=100.0,
                source="ev_profile_with_charger_assignment",
                ev_name=profile.name or f"{profile.manufacturer} {profile.model}".strip(),
                warnings=tuple(warnings),
            )
        if _matches_mercedes_eqe(profile):
            return ResolvedEvId(
                heartbeat_ev_id=profile.heartbeat_ev_id,
                confidence_pct=95.0,
                source="mercedes_eqe_match",
                ev_name=profile.name or f"{profile.manufacturer} {profile.model}".strip(),
                warnings=tuple(warnings),
            )
        return ResolvedEvId(
            heartbeat_ev_id=profile.heartbeat_ev_id,
            confidence_pct=85.0,
            source="single_ev_profile",
            ev_name=profile.name or f"{profile.manufacturer} {profile.model}".strip(),
            warnings=tuple(warnings),
        )

    if mercedes_matches:
        if len(mercedes_matches) == 1:
            profile = mercedes_matches[0]
            assignment = assignment_by_ev.get(profile.heartbeat_ev_id)
            confidence = 100.0 if assignment and assignment.matched else 95.0
            return ResolvedEvId(
                heartbeat_ev_id=profile.heartbeat_ev_id,
                confidence_pct=confidence,
                source="mercedes_eqe_match",
                ev_name=profile.name or f"{profile.manufacturer} {profile.model}".strip(),
                warnings=tuple(warnings),
            )
        warnings.append("Multiple Mercedes/EQE profiles found")

    if len(profiles) > 1:
        warnings.append(f"{len(profiles)} EV profiles found — ambiguous mapping")
        best = profiles[0]
        return ResolvedEvId(
            heartbeat_ev_id=best.heartbeat_ev_id,
            confidence_pct=60.0,
            source="weak_multi_profile_match",
            ev_name=best.name or f"{best.manufacturer} {best.model}".strip(),
            warnings=tuple(warnings),
        )

    return ResolvedEvId(
        heartbeat_ev_id=None,
        confidence_pct=0.0,
        source="none",
        ev_name=None,
        warnings=("No usable EV ID",),
    )
