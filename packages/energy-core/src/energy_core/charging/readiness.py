"""Operational readiness checks for smart charging."""

from __future__ import annotations

import os
from dataclasses import dataclass

from energy_core.chargers.chargeamps_config import build_chargeamps_connection_info
from energy_core.db.models import EvChargerModel, SiteModel


@dataclass(frozen=True, slots=True)
class ChargerReadinessIssue:
    site_slug: str
    charger_id: int
    charger_name: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ChargingReadinessReport:
    ready: bool
    chargeamps_ready: bool
    active_bridge_chargers: int
    issues: tuple[ChargerReadinessIssue, ...]
    notes: tuple[str, ...]


def evaluate_charging_readiness(
    chargers: list[tuple[EvChargerModel, SiteModel]],
) -> ChargingReadinessReport:
    charger_api_keys_configured = sum(1 for charger, _ in chargers if charger.chargeamps_api_key)
    chargeamps = build_chargeamps_connection_info(
        charger_api_keys_configured=charger_api_keys_configured,
    )
    notes = list(chargeamps.notes)
    issues: list[ChargerReadinessIssue] = []
    active = 0

    for charger, site in chargers:
        if not charger.bridge_enabled:
            continue
        active += 1

        if not site.external_system_id:
            issues.append(
                ChargerReadinessIssue(
                    site_slug=site.slug,
                    charger_id=charger.id,
                    charger_name=charger.name,
                    code="missing_system_id",
                    message="HeartBeat system-ID saknas på anläggningen.",
                )
            )
        if not charger.chargeamp_charger_id:
            issues.append(
                ChargerReadinessIssue(
                    site_slug=site.slug,
                    charger_id=charger.id,
                    charger_name=charger.name,
                    code="missing_chargeamp_id",
                    message="Charge Amps laddbox-ID saknas.",
                )
            )
        if not charger.chargeamps_api_key and not os.getenv("CHARGEAMPS_API_KEY", "").strip():
            provider = os.getenv("CHARGEAMPS_PROVIDER", "").strip().lower()
            has_web = bool(os.getenv("CHARGEAMPS_EMAIL", "").strip()) and bool(
                os.getenv("CHARGEAMPS_PASSWORD", "").strip()
            )
            if provider != "web" and not (provider == "" and has_web):
                issues.append(
                    ChargerReadinessIssue(
                        site_slug=site.slug,
                        charger_id=charger.id,
                        charger_name=charger.name,
                        code="missing_api_key",
                        message="Varken per-laddbox-nyckel, CHARGEAMPS_API_KEY eller web-inloggning är konfigurerad.",
                    )
                )
        if site.main_fuse_a is None:
            notes.append(f"{site.slug}/{charger.name}: huvudsäkring (main_fuse_a) saknas — säkringsskydd inaktivt.")

    ready = chargeamps.ready and active > 0 and not issues
    if active == 0:
        notes = (*notes, "Ingen laddbox har bridge aktiv.")
    return ChargingReadinessReport(
        ready=ready,
        chargeamps_ready=chargeamps.ready,
        active_bridge_chargers=active,
        issues=tuple(issues),
        notes=tuple(dict.fromkeys(notes)),
    )
