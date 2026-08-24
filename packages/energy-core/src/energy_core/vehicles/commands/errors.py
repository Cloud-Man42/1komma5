"""Vehicle command errors."""

from __future__ import annotations


class VehicleCommandError(Exception):
    def __init__(self, message: str, *, code: str = "command_failed") -> None:
        super().__init__(message)
        self.code = code


class VehicleCommandsDisabledError(VehicleCommandError):
    def __init__(self) -> None:
        super().__init__(
            "Mercedes commands are disabled for this site",
            code="commands_disabled",
        )


class VehicleCapabilityUnavailableError(VehicleCommandError):
    def __init__(self, capability: str) -> None:
        super().__init__(
            f"Vehicle capability unavailable: {capability}",
            code="capability_unavailable",
        )
