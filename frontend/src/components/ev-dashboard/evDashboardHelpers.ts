import type {
  EnergyBalanceSnapshot,
  EnergyReasoning,
  EvCharger,
  EvChargingSession,
  EvChargingStats,
  EvEnergySources,
  EvSolarChargingPlan,
} from "@/lib/api";
import { formatDeadline } from "@/lib/deadlineInput";
import { formatSekAmount } from "@/lib/prices";

export const EV_MODE_LABELS: Record<string, string> = {
  SMART_CHARGE: "Smart laddning",
  PRICE_CHARGE: "Billigast pris",
  SOLAR_CHARGE: "Solel",
  QUICK_CHARGE: "Snabbladdning",
  PAUSED: "Pausad",
};

/** kg CO₂ avoided per kWh renewable vs fossil car (approx. Swedish factor). */
export const CO2_SAVED_KG_PER_RENEWABLE_KWH = 0.155;

export type EvStatsPeriod = "day" | "week" | "month" | "year";

export interface EvPowerChartPoint {
  label: string;
  sortKey: number;
  powerKw: number;
}

export interface EvHourlySourcePoint {
  label: string;
  solar: number;
  battery: number;
  gridCheap: number;
  gridExpensive: number;
}

export interface EvEnergyMixSlice {
  id: string;
  label: string;
  kwh: number;
  pct: number;
  color: string;
}

export interface EvSavingsChartPoint {
  label: string;
  actual: number;
  baseline: number;
}

export interface EvPlanWindow {
  id: string;
  label: string;
  time: string;
  color: string;
}

export function modeLabel(mode: string | null | undefined): string {
  if (!mode) return "—";
  return EV_MODE_LABELS[mode] ?? mode;
}

export function formatEvKwh(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: digits, minimumFractionDigits: digits })} kWh`;
}

export function formatEvDuration(start: string, end: string | null): string {
  const startMs = new Date(start).getTime();
  const endMs = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) return "—";
  const minutes = Math.max(0, Math.round((endMs - startMs) / 60_000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  return rem > 0 ? `${hours} h ${rem} min` : `${hours} h`;
}

export function formatEvSessionTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("sv-SE", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatEvCurrent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toFixed(1)} A`;
}

export function formatEvPowerW(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "0 W";
  const abs = Math.abs(value);
  if (abs >= 1000) return `${(value / 1000).toFixed(1)} kW`;
  return `${Math.round(value)} W`;
}

export function renewableKwhFromSources(sources: EvEnergySources): number {
  return (sources.solar_direct_kwh ?? 0) + (sources.solar_battery_kwh ?? 0);
}

export function batteryKwhFromSources(sources: EvEnergySources): number {
  return sources.solar_battery_kwh + sources.grid_battery_kwh;
}

export function gridKwhFromSources(sources: EvEnergySources): number {
  return sources.grid_direct_kwh + sources.grid_battery_kwh;
}

export function computeCo2SavedKg(stats: EvChargingStats | null): number | null {
  if (!stats || stats.total_energy_kwh <= 0) return null;
  const renewableKwh =
    renewableKwhFromSources(stats.energy_sources) ||
    stats.total_energy_kwh * (stats.renewable_share_percent / 100);
  return renewableKwh * CO2_SAVED_KG_PER_RENEWABLE_KWH;
}

export function sessionSourceLabel(session: EvChargingSession): { label: string; tone: string } {
  const s = session.energy_sources;
  const solar = renewableKwhFromSources(s);
  const grid = s.grid_direct_kwh + s.grid_battery_kwh;
  const battery = s.solar_battery_kwh + s.grid_battery_kwh;
  if (solar > 0 && battery > 0) return { label: "Sol + Batteri", tone: "mixed" };
  if (solar > 0 && grid <= 0.01) return { label: "Sol", tone: "solar" };
  if (grid > 0 && solar <= 0.01) {
    const avg = session.average_cost_sek_per_kwh;
    return { label: avg != null && avg < 1.5 ? "Nät (lågpris)" : "Nät (dyrt)", tone: "grid" };
  }
  if (solar > 0) return { label: "Sol + Nät", tone: "mixed" };
  return { label: "Nät", tone: "grid" };
}

export function buildPowerChartFromHistory(items: EnergyBalanceSnapshot[]): EvPowerChartPoint[] {
  return items
    .filter((item) => item.recorded_at)
    .map((item) => {
      const date = new Date(item.recorded_at!);
      return {
        label: date.toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }),
        sortKey: date.getTime(),
        powerKw: Math.max(0, (item.halo_power_w ?? item.virtual_evse_reported_power_w ?? 0) / 1000),
      };
    })
    .sort((a, b) => a.sortKey - b.sortKey);
}

export function maxPowerTodayKw(items: EnergyBalanceSnapshot[]): number {
  return Math.max(0, ...items.map((i) => (i.halo_power_w ?? 0) / 1000));
}

export function buildEnergyMixSlices(stats: EvChargingStats | null): EvEnergyMixSlice[] {
  if (!stats || stats.total_energy_kwh <= 0) {
    return [
      { id: "solar", label: "Sol", kwh: 0, pct: 0, color: "#4ade80" },
      { id: "battery", label: "Batteri", kwh: 0, pct: 0, color: "#38bdf8" },
      { id: "grid-cheap", label: "Nät (lågpris)", kwh: 0, pct: 0, color: "#fbbf24" },
      { id: "grid-expensive", label: "Nät (dyrt)", kwh: 0, pct: 0, color: "#f87171" },
    ];
  }
  const total = stats.total_energy_kwh || 1;
  const s = stats.energy_sources;
  const solar = s.solar_direct_kwh;
  const battery = batteryKwhFromSources(s);
  const grid = gridKwhFromSources(s);
  const avgPrice = stats.average_cost_sek_per_kwh;
  const cheapRatio = avgPrice != null && avgPrice < 1.5 ? 0.65 : 0.35;
  const gridCheap = grid * cheapRatio;
  const gridExpensive = Math.max(0, grid - gridCheap);
  const slices = [
    { id: "solar", label: "Sol", kwh: solar, pct: (solar / total) * 100, color: "#4ade80" },
    { id: "battery", label: "Batteri", kwh: battery, pct: (battery / total) * 100, color: "#38bdf8" },
    { id: "grid-cheap", label: "Nät (lågpris)", kwh: gridCheap, pct: (gridCheap / total) * 100, color: "#fbbf24" },
    { id: "grid-expensive", label: "Nät (dyrt)", kwh: gridExpensive, pct: (gridExpensive / total) * 100, color: "#f87171" },
  ];
  return slices;
}

export function buildHourlySourceChart(sessions: EvChargingSession[]): EvHourlySourcePoint[] {
  const buckets = Array.from({ length: 24 }, (_, hour) => ({
    label: `${String(hour).padStart(2, "0")}:00`,
    solar: 0,
    battery: 0,
    gridCheap: 0,
    gridExpensive: 0,
  }));

  for (const session of sessions) {
    for (const interval of session.intervals ?? []) {
      const hour = new Date(interval.start_time).getHours();
      if (hour < 0 || hour > 23) continue;
      const s = interval.energy_sources;
      buckets[hour].solar += s.solar_direct_kwh;
      buckets[hour].battery += s.solar_battery_kwh + s.grid_battery_kwh;
      const grid = s.grid_direct_kwh;
      const price = interval.electricity_price_sek_kwh;
      if (price != null && price < 1.5) buckets[hour].gridCheap += grid;
      else buckets[hour].gridExpensive += grid;
    }
  }

  return buckets;
}

export function buildSavingsChart(sessions: EvChargingSession[]): EvSavingsChartPoint[] {
  const byDay = new Map<string, { actual: number; baseline: number }>();
  for (const session of sessions) {
    if (!session.ended_at) continue;
    const key = session.ended_at.slice(0, 10);
    const entry = byDay.get(key) ?? { actual: 0, baseline: 0 };
    entry.actual += session.actual_cost_sek ?? 0;
    entry.baseline += session.reference_cost_sek ?? session.actual_cost_sek ?? 0;
    byDay.set(key, entry);
  }
  const sorted = [...byDay.entries()].sort(([a], [b]) => a.localeCompare(b));
  let cumActual = 0;
  let cumBaseline = 0;
  return sorted.map(([day, values]) => {
    cumActual += values.actual;
    cumBaseline += values.baseline;
    const date = new Date(day);
    return {
      label: date.toLocaleDateString("sv-SE", { day: "numeric", month: "short" }),
      actual: cumBaseline - cumActual,
      baseline: 0,
    };
  });
}

export function buildPlanWindows(
  plan: EvSolarChargingPlan | null,
  reasoning: EnergyReasoning | null,
): EvPlanWindow[] {
  const windows: EvPlanWindow[] = [];
  if (plan?.expected_solar_window_start && plan.expected_solar_window_end) {
    const start = new Date(plan.expected_solar_window_start).toLocaleTimeString("sv-SE", {
      hour: "2-digit",
      minute: "2-digit",
    });
    const end = new Date(plan.expected_solar_window_end).toLocaleTimeString("sv-SE", {
      hour: "2-digit",
      minute: "2-digit",
    });
    windows.push({ id: "solar", label: "Solöverskott", time: `${start}–${end}`, color: "#fbbf24" });
  }
  if (plan?.cheapest_grid_window) {
    windows.push({
      id: "cheap",
      label: "Billigaste timmar",
      time: plan.cheapest_grid_window,
      color: "#c084fc",
    });
  }
  if (reasoning?.price_tier === "red") {
    windows.push({ id: "avoid", label: "Undvik", time: "17:00–21:00", color: "#f87171" });
  }
  return windows;
}

export function nextChargeWindowLabel(plan: EvSolarChargingPlan | null): string {
  if (plan?.expected_solar_window_start) {
    const start = new Date(plan.expected_solar_window_start);
    if (!Number.isNaN(start.getTime())) {
      return `${start.toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" })} Idag`;
    }
  }
  if (plan?.cheapest_grid_window) return plan.cheapest_grid_window;
  return "—";
}

export function priceTierDisplay(reasoning: EnergyReasoning | null): {
  label: string;
  detail: string;
  tone: "green" | "normal" | "red" | "unknown";
} {
  const tier = reasoning?.price_tier ?? "unknown";
  const price = reasoning?.current_price_eur_kwh;
  const ore =
    price != null ? Math.round(price * 11.2 * 100) : null;
  if (tier === "green") return { label: "Grönt (billigt)", detail: ore != null ? `${ore} öre/kWh` : "—", tone: "green" };
  if (tier === "red") return { label: "Rött (dyrt)", detail: ore != null ? `${ore} öre/kWh` : "—", tone: "red" };
  if (tier === "normal") return { label: "Normalt", detail: ore != null ? `${ore} öre/kWh` : "—", tone: "normal" };
  return { label: "Okänt", detail: "—", tone: "unknown" };
}

export function uplinkLabel(charger: EvCharger, bridgeStale: boolean | null): string {
  if (bridgeStale) return "Svag";
  if (charger.connection_status === "connected" || charger.last_halo_connected) return "Utmärkt";
  if (charger.connection_status === "error") return "Fel";
  return "—";
}

export function deadlineHeaderLabel(deadlineAt: string | null | undefined): string {
  const formatted = formatDeadline(deadlineAt);
  return formatted ?? "—";
}

export function averageSessionCostOre(stats: EvChargingStats | null): string {
  if (!stats?.average_cost_sek_per_kwh) return "—";
  return `${Math.round(stats.average_cost_sek_per_kwh * 100)} öre/kWh`;
}

export function formatMonthCost(stats: EvChargingStats | null): string {
  if (!stats) return "—";
  return formatSekAmount(stats.actual_cost_sek).label;
}

export function isHaloCharger(charger: EvCharger): boolean {
  const label = `${charger.manufacturer} ${charger.model} ${charger.name}`.toLowerCase();
  return label.includes("halo") || label.includes("chargeamp") || label.includes("charge amps");
}

export function totalChargeMinutesToday(sessions: EvChargingSession[]): number {
  const today = new Date().toISOString().slice(0, 10);
  let minutes = 0;
  for (const session of sessions) {
    if (!session.started_at.startsWith(today)) continue;
    const start = new Date(session.started_at).getTime();
    const end = session.ended_at ? new Date(session.ended_at).getTime() : Date.now();
    minutes += Math.max(0, (end - start) / 60_000);
  }
  return minutes;
}

export function averagePowerTodayKw(sessions: EvChargingSession[], historyMaxKw: number): number {
  const todaySessions = sessions.filter((s) => s.started_at.startsWith(new Date().toISOString().slice(0, 10)));
  if (todaySessions.length === 0) return historyMaxKw > 0 ? 0 : 0;
  let weighted = 0;
  let hours = 0;
  for (const session of todaySessions) {
    for (const interval of session.intervals ?? []) {
      const durationH =
        (new Date(interval.end_time).getTime() - new Date(interval.start_time).getTime()) / 3_600_000;
      if (durationH > 0 && interval.average_charging_power_w) {
        weighted += (interval.average_charging_power_w / 1000) * durationH;
        hours += durationH;
      }
    }
  }
  return hours > 0 ? weighted / hours : 0;
}
