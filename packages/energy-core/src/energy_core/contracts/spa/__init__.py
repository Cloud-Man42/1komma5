"""Spa contracts."""

from energy_core.contracts.spa.control import ISpaControl, ISpaControlService
from energy_core.contracts.spa.errors import SpaControlError
from energy_core.contracts.spa.status import SpaStatus

__all__ = ["ISpaControl", "ISpaControlService", "SpaControlError", "SpaStatus"]
