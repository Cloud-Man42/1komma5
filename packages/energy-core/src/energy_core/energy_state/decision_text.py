"""Central Swedish decision text for EMIC operating state."""

from __future__ import annotations

from energy_core.energy_state.models import (
    BatteryState,
    EnergySiteSnapshot,
    EvState,
    SmartChargingState,
    SystemStatus,
)


class EnergyDecisionTextService:
    """Generate a short Swedish sentence describing what EMIC is doing."""

    @staticmethod
    def build(snapshot: EnergySiteSnapshot) -> str:
        if snapshot.system_status == SystemStatus.OFFLINE:
            return "Ingen färsk mätdata från anläggningen"

        if snapshot.battery_state == BatteryState.FULL:
            return "Batteriet är fullt"

        if snapshot.battery_state == BatteryState.CHARGING:
            solar = snapshot.solar_power_kw or 0.0
            import_kw = snapshot.grid_import_power_kw or 0.0
            if solar > 0.5 and import_kw < 0.1:
                return "Laddar batteriet med solel"
            if import_kw > 0.1:
                return "Köper billig el och laddar batteriet"
            return "Laddar batteriet"

        if snapshot.battery_state == BatteryState.DISCHARGING:
            import_kw = snapshot.grid_import_power_kw or 0.0
            if import_kw < 0.1:
                return "Driver huset från batteriet"
            return "Urladdar batteriet"

        export = snapshot.grid_export_power_kw or 0.0
        if export > 0.1:
            return "Säljer solelöverskott"

        import_kw = snapshot.grid_import_power_kw or 0.0
        if import_kw > 0.1:
            return "Köper el från nätet"

        if snapshot.ev_state == EvState.WAITING:
            if snapshot.smart_charging_state == SmartChargingState.WAITING_FOR_SURPLUS:
                return "Bilen väntar på större solelöverskott"
            return "Bilen väntar på billigare el"

        if snapshot.ev_state == EvState.CHARGING:
            solar = snapshot.solar_power_kw or 0.0
            export_kw = snapshot.grid_export_power_kw or 0.0
            if solar > 0.5 and export_kw > 0.1:
                return "Bilen laddas med solelöverskott"
            return "Bilen laddar"

        if snapshot.operating_mode:
            return snapshot.operating_mode

        return "Övervakar energiflödet"
