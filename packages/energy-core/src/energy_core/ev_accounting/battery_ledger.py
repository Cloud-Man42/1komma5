"""Weighted-average battery energy ledger."""

from __future__ import annotations

from dataclasses import replace

from energy_core.ev_accounting.models import BatteryDischargeSplit, BatteryLedgerState, SiteEnergySample


class BatteryEnergyLedgerService:
    """
    Track battery stored energy origin using weighted-average attribution.

    When battery charges:
      - solar-origin increases by solar-attributable charge
      - grid-origin increases by remainder, with cost basis

    When battery discharges:
      - withdraw proportionally from solar and grid pools
      - return split for EV attribution (SOLAR_VIA_BATTERY / GRID_VIA_BATTERY)
    """

    def update(
        self,
        ledger: BatteryLedgerState,
        sample: SiteEnergySample,
        *,
        grid_price_sek_kwh: float,
    ) -> tuple[BatteryLedgerState, BatteryDischargeSplit | None]:
        state = ledger
        discharge_split: BatteryDischargeSplit | None = None

        if sample.battery_charge_kwh > 0:
            state = self._apply_charge(state, sample, grid_price_sek_kwh=grid_price_sek_kwh)

        if sample.battery_discharge_kwh > 0:
            state, discharge_split = self._apply_discharge(state, sample.battery_discharge_kwh)

        return state, discharge_split

    def _apply_charge(
        self,
        ledger: BatteryLedgerState,
        sample: SiteEnergySample,
        *,
        grid_price_sek_kwh: float,
    ) -> BatteryLedgerState:
        charge_kwh = sample.battery_charge_kwh
        # Conservative solar charge: PV surplus after house load, capped by charge amount
        pv_surplus_kwh = max(0.0, sample.pv_kwh - sample.house_kwh)
        if sample.grid_export_kwh > 0:
            pv_surplus_kwh = max(pv_surplus_kwh, sample.grid_export_kwh)
        solar_charge = min(charge_kwh, pv_surplus_kwh)
        grid_charge = max(0.0, charge_kwh - solar_charge)

        return BatteryLedgerState(
            solar_energy_kwh=ledger.solar_energy_kwh + solar_charge,
            grid_energy_kwh=ledger.grid_energy_kwh + grid_charge,
            grid_energy_cost_sek=ledger.grid_energy_cost_sek + grid_charge * grid_price_sek_kwh,
        )

    def _apply_discharge(
        self,
        ledger: BatteryLedgerState,
        discharge_kwh: float,
    ) -> tuple[BatteryLedgerState, BatteryDischargeSplit]:
        total = ledger.total_kwh
        if total <= 0 or discharge_kwh <= 0:
            return ledger, BatteryDischargeSplit(0.0, 0.0, 0.0)

        actual_discharge = min(discharge_kwh, total)
        solar_fraction = ledger.solar_energy_kwh / total
        grid_fraction = ledger.grid_energy_kwh / total

        solar_out = actual_discharge * solar_fraction
        grid_out = actual_discharge * grid_fraction
        grid_cost_out = ledger.grid_energy_cost_sek * (grid_out / ledger.grid_energy_kwh) if ledger.grid_energy_kwh > 0 else 0.0

        new_state = BatteryLedgerState(
            solar_energy_kwh=max(0.0, ledger.solar_energy_kwh - solar_out),
            grid_energy_kwh=max(0.0, ledger.grid_energy_kwh - grid_out),
            grid_energy_cost_sek=max(0.0, ledger.grid_energy_cost_sek - grid_cost_out),
        )
        return new_state, BatteryDischargeSplit(solar_kwh=solar_out, grid_kwh=grid_out, grid_cost_sek=grid_cost_out)
