import type { SpaEnergyPeriod, SpaStatus } from "@/lib/api";
import { SpaSemiGauge } from "./SpaSemiGauge";
import {
  formatCostKr,
  formatKwh,
  formatKwFromW,
  isHeaterLive,
  tempStable,
} from "./spaDashboardHelpers";

export function SpaGaugeRow({
  status,
  today,
  month,
  total,
}: {
  status: SpaStatus;
  today: SpaEnergyPeriod | null;
  month: SpaEnergyPeriod | null;
  total: SpaEnergyPeriod | null;
}) {
  const temp = status.water_temperature_c ?? 0;
  const powerW = status.current_power_w ?? 0;
  const heating = isHeaterLive(status);
  const tempLabel = tempStable(status)
    ? heating
      ? "Stabil · värmer"
      : "Stabil"
    : heating
      ? "Värmer"
      : "Reglerar";

  return (
    <div className="sdash-gauge-row">
      <SpaSemiGauge
        title="VATTENTEMPERATUR"
        value={Math.max(0, temp - 35)}
        max={5}
        displayValue={`${temp.toFixed(1)}°C`}
        minLabel="35°C"
        maxLabel="40°C"
        accent="#38bdf8"
        accentGlow="#7dd3fc"
        statusLabel={tempLabel}
        statusOk={tempStable(status) && !heating}
        footer={
          status.set_temperature_c != null ? `Mål: ${status.set_temperature_c.toFixed(1)}°C` : undefined
        }
      />
      <SpaSemiGauge
        title="ENERGIFÖRBRUKNING"
        value={powerW / 1000}
        max={6}
        displayValue={formatKwFromW(powerW)}
        minLabel="0"
        maxLabel="6 kW"
        accent="#22d3ee"
        accentGlow="#67e8f9"
        footer={today?.energy_kwh != null ? `Idag totalt: ${formatKwh(today.energy_kwh)}` : undefined}
      />
      <SpaSemiGauge
        title="DAGENS FÖRBRUKNING"
        value={today?.energy_kwh ?? 0}
        max={40}
        displayValue={formatKwh(today?.energy_kwh ?? 0)}
        minLabel="0"
        maxLabel="40 kWh"
        accent="#4ade80"
        accentGlow="#86efac"
        footer={today ? `Kostnad: ${formatCostKr(today.actual_cost_sek)}` : undefined}
      />
      <SpaSemiGauge
        title="MÅNADSFÖRBRUKNING"
        value={month?.energy_kwh ?? 0}
        max={600}
        displayValue={formatKwh(month?.energy_kwh ?? 0, 0)}
        minLabel="0"
        maxLabel="600 kWh"
        accent="#a78bfa"
        accentGlow="#c4b5fd"
        footer={month ? `Kostnad: ${formatCostKr(month.actual_cost_sek)}` : undefined}
      />
      <SpaSemiGauge
        title="TOTAL FÖRBRUKNING"
        value={total?.energy_kwh ?? 0}
        max={10000}
        displayValue={formatKwh(total?.energy_kwh ?? 0, 0)}
        minLabel="0"
        maxLabel="10k kWh"
        accent="#fbbf24"
        accentGlow="#fde047"
        footer={total ? `Kostnad: ${formatCostKr(total.actual_cost_sek)}` : undefined}
      />
    </div>
  );
}
