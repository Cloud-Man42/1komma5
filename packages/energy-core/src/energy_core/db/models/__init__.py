"""ORM models split by domain. Import all modules so Base.metadata is complete."""

from __future__ import annotations

from energy_core.db.models.base import Base

from energy_core.db.models.balance import *  # noqa: F403
from energy_core.db.models.charging_stations import *  # noqa: F403
from energy_core.db.models.consumer import *  # noqa: F403
from energy_core.db.models.energy_control import *  # noqa: F403
from energy_core.db.models.ev import *  # noqa: F403
from energy_core.db.models.heartbeat import *  # noqa: F403
from energy_core.db.models.pricing import *  # noqa: F403
from energy_core.db.models.readings import *  # noqa: F403
from energy_core.db.models.sites import *  # noqa: F403
from energy_core.db.models.solar import *  # noqa: F403
from energy_core.db.models.spa import *  # noqa: F403
from energy_core.db.models.system import *  # noqa: F403
from energy_core.db.models.modules import *  # noqa: F403
from energy_core.db.models.installed_module_package import *  # noqa: F403
from energy_core.db.models.module_publisher_key import *  # noqa: F403
from energy_core.db.models.module_publisher import *  # noqa: F403
from energy_core.db.models.module_publisher_verification import *  # noqa: F403
from energy_core.db.models.module_ownership import *  # noqa: F403
from energy_core.db.models.module_ownership_transfer import *  # noqa: F403
from energy_core.db.models.module_installation_policy import *  # noqa: F403
from energy_core.db.models.marketplace_trust_cache import *  # noqa: F403
from energy_core.db.models.marketplace_distribution import *  # noqa: F403
from energy_core.db.models.isolated_runtime import *  # noqa: F403
from energy_core.db.models.runtime_pilot_authorization import *  # noqa: F403
from energy_core.db.models.climate_device_reading import *  # noqa: F403
from energy_core.db.models.vehicles import *  # noqa: F403
from energy_core.db.models.users import *  # noqa: F403

__all__ = [name for name in dir() if not name.startswith('_')]

