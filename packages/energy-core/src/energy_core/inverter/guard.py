"""Read-only guard for inverter control paths in Phase 1."""

from __future__ import annotations

import inspect
from typing import Any


class InverterControlForbiddenError(RuntimeError):
    """Raised when code attempts to write or control the physical inverter."""


_FORBIDDEN_WRITE_NAMES = frozenset(
    {
        "write_register",
        "write_registers",
        "set_operating_mode",
        "set_charge_power",
        "set_discharge_power",
        "set_export_limit",
        "set_battery_reserve",
        "send_control_command",
        "modbus_write",
    }
)


def assert_inverter_read_only(*, operation: str) -> None:
    """Block inverter write/control operations in Phase 1."""
    normalized = operation.strip().lower()
    if (
        normalized in _FORBIDDEN_WRITE_NAMES
        or normalized.startswith("write_")
        or normalized.startswith("set_")
    ):
        raise InverterControlForbiddenError(
            f"Inverter control '{operation}' is forbidden in Phase 1 (read-only telemetry only)."
        )


def guard_inverter_client(client: Any) -> Any:
    """Wrap a client so any write-like method raises InverterControlForbiddenError."""

    class _ReadOnlyProxy:
        def __getattr__(self, name: str) -> Any:
            target = getattr(client, name)
            if not callable(target):
                return target

            async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
                assert_inverter_read_only(operation=name)
                return await target(*args, **kwargs)

            def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                assert_inverter_read_only(operation=name)
                return target(*args, **kwargs)

            if inspect.iscoroutinefunction(target):
                return _async_wrapper
            return _sync_wrapper

    return _ReadOnlyProxy()


# Modules allowed to reference inverter read paths only (no Modbus clients in Phase 1).
ALLOWED_INVERTER_MODULES = frozenset(
    {
        "energy_core.inverter.guard",
        "energy_core.sungrow.types",
        "energy_core.sungrow.heartbeat_provider",
        "energy_core.energy_balance.engine",
        "energy_core.energy_balance.correlation",
        "energy_core.energy_balance.coordinator",
    }
)
