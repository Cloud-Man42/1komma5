"""Contract telemetry constant tests."""

from energy_core.contracts.telemetry import STALE_TELEMETRY_SECONDS
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS as MERCEDES_SHIM


def test_stale_telemetry_seconds_is_canonical() -> None:
    assert STALE_TELEMETRY_SECONDS == 300


def test_mercedes_shim_reexports_canonical_value() -> None:
    assert MERCEDES_SHIM == STALE_TELEMETRY_SECONDS
