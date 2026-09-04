from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.energy_control.noop_provider import NoopControlProvider
from energy_core.energy_control.provider import IEnergyControlProvider


def resolve_control_provider(
    settings: Settings | None = None,
    *,
    session: AsyncSession | None = None,
) -> IEnergyControlProvider:
    settings = settings or get_settings()
    provider = (settings.energy_control_provider or "noop").strip().lower()
    if provider in {"noop", "noop-dry-run", ""}:
        return NoopControlProvider()
    if provider == "heartbeat":
        if session is None:
            raise ValueError("Heartbeat control provider requires database session")
        from energy_core.energy_control.heartbeat_provider import HeartbeatControlProvider

        return HeartbeatControlProvider(session)
    if provider in {"chargeamps", "charge-amps", "charge_amps"}:
        if session is None:
            raise ValueError("Charge Amps control provider requires database session")
        from energy_core.energy_control.chargeamps_provider import ChargeAmpsControlProvider

        return ChargeAmpsControlProvider(session)
    raise ValueError(f"Unknown energy control provider '{provider}'")

def default_control_provider() -> IEnergyControlProvider:
    return resolve_control_provider()
