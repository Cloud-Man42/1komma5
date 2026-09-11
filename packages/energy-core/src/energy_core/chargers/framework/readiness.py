"""Vendor-neutral Charge Amps readiness projection for feature modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChargeAmpsReadiness:
    ready: bool
    provider: str
    notes: tuple[str, ...]


def build_chargeamps_readiness(*, charger_api_keys_configured: int) -> ChargeAmpsReadiness:
    from energy_core.integrations.chargeamps.config import build_chargeamps_connection_info

    info = build_chargeamps_connection_info(
        charger_api_keys_configured=charger_api_keys_configured,
    )
    return ChargeAmpsReadiness(
        ready=info.ready,
        provider=info.effective_provider,
        notes=tuple(info.notes),
    )
