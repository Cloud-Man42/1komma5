"""Vehicle charge session engine."""

__all__ = ["VehicleChargeSessionCoordinator"]


def __getattr__(name: str):
    if name == "VehicleChargeSessionCoordinator":
        from energy_core.vehicles.sessions.coordinator import VehicleChargeSessionCoordinator

        return VehicleChargeSessionCoordinator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
