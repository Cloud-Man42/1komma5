from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.energy_control.noop_provider import NoopControlProvider
from energy_core.energy_control.provider import IEnergyControlProvider

ProviderFactory = Callable[[Settings, AsyncSession | None], IEnergyControlProvider]


def _noop_factory(settings: Settings, session: AsyncSession | None) -> IEnergyControlProvider:
    _ = settings, session
    return NoopControlProvider()


def _heartbeat_factory(settings: Settings, session: AsyncSession | None) -> IEnergyControlProvider:
    _ = settings
    if session is None:
        raise ValueError("Heartbeat control provider requires database session")
    from energy_core.energy_control.heartbeat_provider import HeartbeatControlProvider

    return HeartbeatControlProvider(session)


def _chargeamps_factory(settings: Settings, session: AsyncSession | None) -> IEnergyControlProvider:
    _ = settings
    if session is None:
        raise ValueError("Charge Amps control provider requires database session")
    from energy_core.integrations.chargeamps.control_provider import ChargeAmpsControlProvider

    return ChargeAmpsControlProvider(session)


_CONTROL_PROVIDER_REGISTRY: dict[str, ProviderFactory] = {
    "noop": _noop_factory,
    "noop-dry-run": _noop_factory,
    "": _noop_factory,
    "heartbeat": _heartbeat_factory,
    "chargeamps": _chargeamps_factory,
    "charge-amps": _chargeamps_factory,
    "charge_amps": _chargeamps_factory,
}


def resolve_control_provider(
    settings: Settings | None = None,
    *,
    session: AsyncSession | None = None,
) -> IEnergyControlProvider:
    settings = settings or get_settings()
    provider = (settings.energy_control_provider or "noop").strip().lower()
    factory = _CONTROL_PROVIDER_REGISTRY.get(provider)
    if factory is None:
        raise ValueError(f"Unknown energy control provider '{provider}'")
    return factory(settings, session)


def default_control_provider() -> IEnergyControlProvider:
    return resolve_control_provider()
