"""Build flexible-load specs for smart EV chargers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.charging.policy import SMART_MODES, normalized_mode, uses_price_optimization
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.flexible_load.orchestrator import OrchestratedLoadSpec
from energy_core.flexible_load.types import FlexibleLoad, LoadStrategy


def build_ev_orchestrated_load(
    charger: EvChargerModel,
    site: SiteModel,
    *,
    now: datetime,
) -> OrchestratedLoadSpec | None:
    mode = normalized_mode(charger.charging_mode)
    if not uses_price_optimization(charger.charging_mode, override_active=False) and mode not in SMART_MODES:
        return None
    if not charger.bridge_enabled:
        return None
    if charger.last_vehicle_connected is False:
        return None

    power_w = charger.max_power_w
    if power_w is None:
        power_w = charger.max_current_a * charger.phases * charger.nominal_voltage_v

    deadline = charger.deadline_at or (now + timedelta(hours=12))
    latest_finish = min(deadline, now + timedelta(hours=24))

    load = FlexibleLoad(
        load_id=f"ev_charger_{charger.id}",
        name=f"EV {charger.name}",
        nominal_power_w=power_w,
        minimum_runtime=timedelta(hours=1),
        maximum_runtime=timedelta(hours=6),
        earliest_start=now,
        latest_finish=latest_finish,
        deadline=deadline,
        priority=charger.load_priority,
        interruptible=True,
        safety_critical=False,
    )
    return OrchestratedLoadSpec(
        load=load,
        strategy=LoadStrategy.SMART,
        allow_battery=True,
        prefer_solar=True,
        min_battery_soc_pct=40.0,
        fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
    )
