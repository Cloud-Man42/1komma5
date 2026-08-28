import type { SpaControlConfig, SpaEnergyPeriod, SpaHealth, SpaPlan, SpaStatus } from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

export interface SpaComponentRow {
  id: string;
  label: string;
  powerW: number;
  status: string;
  detail?: string;
}

const FILTER_ACTIVE = new Set(["Filtering", "Boost", "Resuming", "Overtemperature", "Sanitize", "Purge"]);
const UV_TREATMENT_STATUSES = new Set(["Filtering", "Sanitize", "Purge"]);
const MIN_SPA_LOAD_W = 100;
const MIN_PUMP_LOAD_W = 75;
const MIN_HEATER_LOAD_W = 50;

function circulationLoadW(status: SpaStatus): number {
  return Object.entries(status.power_breakdown ?? {})
    .filter(([key]) => ["circulation", "cirkulation", "pump4"].includes(key.toLowerCase()))
    .reduce((sum, [, watts]) => sum + watts, 0);
}

function pumpLoadW(status: SpaStatus): number {
  return Object.entries(status.power_breakdown ?? {})
    .filter(([key]) => key.toLowerCase().includes("pump"))
    .reduce((sum, [, watts]) => sum + watts, 0);
}

function heaterLoadW(status: SpaStatus): number {
  return Object.entries(status.power_breakdown ?? {})
    .filter(([key]) => ["heater", "värmare", "varmare"].includes(key.toLowerCase()))
    .reduce((sum, [, watts]) => sum + watts, 0);
}

function spaLoadW(status: SpaStatus): number {
  if (status.current_power_w != null && status.current_power_w > 0) return status.current_power_w;
  return Object.values(status.power_breakdown ?? {}).reduce((sum, watts) => sum + watts, 0);
}

export function isHeaterLive(status: SpaStatus): boolean {
  if (heaterLoadW(status) >= MIN_HEATER_LOAD_W) return true;
  return Boolean(status.heater_active && spaLoadW(status) >= MIN_SPA_LOAD_W);
}

export function isFilterRunning(status: SpaStatus, _plan: SpaPlan | null = null): boolean {
  if (status.filter_cycle_active != null) return status.filter_cycle_active;
  if (!status.filter_status || !FILTER_ACTIVE.has(status.filter_status)) return false;
  return spaLoadW(status) >= MIN_SPA_LOAD_W || pumpLoadW(status) >= MIN_PUMP_LOAD_W;
}

/** UV inferred from filter/circulation — Eco Pak exposes no UV sensor. */
export function isUvActive(status: SpaStatus): boolean {
  if (!status.filter_status || !UV_TREATMENT_STATUSES.has(status.filter_status)) {
    return false;
  }
  if (status.filter_cycle_active === true) return true;
  if (circulationLoadW(status) >= MIN_PUMP_LOAD_W) return true;
  return pumpLoadW(status) >= MIN_PUMP_LOAD_W;
}

export function sensorStatusLabel(active: boolean | null): string {
  if (active === null) return "Ej rapporterad";
  return active ? "På" : "Av";
}

export function filterProgressPct(
  status: SpaStatus,
  plan: SpaPlan | null,
  _control: SpaControlConfig | null,
): number {
  if (!isFilterRunning(status, plan)) return 0;
  if (plan?.daily_progress_pct != null) return Math.min(100, Math.max(0, plan.daily_progress_pct));
  return 0;
}

export const SPA_STRATEGY_OPTIONS = [
  { id: "SMART", label: "Smart" },
  { id: "SOLAR_ONLY", label: "Endast solel" },
  { id: "CHEAPEST", label: "Billigast" },
  { id: "FIXED_SCHEDULE", label: "Fast schema" },
] as const;

export function strategyHintSv(strategy: string | null | undefined): string | null {
  switch (strategy) {
    case "SMART":
      return "Balanserar solel, elpris och säkerhetskrav.";
    case "SOLAR_ONLY":
      return "Kör filtercykler när solel räcker; fallback vid brådskande behov.";
    case "CHEAPEST":
      return "Placerar filtercyklerna på billigaste timmarna inom fönstret.";
    case "FIXED_SCHEDULE":
      return "Eco Pak styr tiderna inom ett fast fönster — EMIC flyttar inte schemat.";
    default:
      return null;
  }
}

export function shadowModeHintSv(active: boolean): string {
  if (active) {
    return "EMIC planerar och jämför men skickar inga automatiska filterkommandon. Manuell start fungerar fortfarande.";
  }
  return "EMIC kan skicka automatiska filterkommandon till spabadet enligt plan.";
}

export function isFixedScheduleIncomplete(
  control:
    | Pick<SpaControlConfig, "strategy" | "fixed_schedule_start" | "fixed_schedule_end">
    | null
    | undefined,
): boolean {
  if (!control || control.strategy !== "FIXED_SCHEDULE") return false;
  return !control.fixed_schedule_start || !control.fixed_schedule_end;
}

export function recommendedFixedScheduleTimes(
  control: Pick<SpaControlConfig, "allowed_window_start" | "allowed_window_end">,
): { start: string; end: string } {
  return {
    start: control.allowed_window_start || "07:00",
    end: control.allowed_window_end || "22:00",
  };
}

export function fixedScheduleWarningSv(
  control:
    | Pick<
        SpaControlConfig,
        | "strategy"
        | "fixed_schedule_start"
        | "fixed_schedule_end"
        | "filter_optimization_enabled"
        | "shadow_mode"
      >
    | null
    | undefined,
): string | null {
  if (!isFixedScheduleIncomplete(control)) return null;
  const parts = [
    "Fast schema saknar start- och sluttid — tills du fyller i dem kan EMIC fortfarande optimera cykeltider som i Smart-läge.",
    "Ange tider så låter du Eco Pak styra filtreringen inom fönstret utan att EMIC flyttar schemat.",
  ];
  if (control?.shadow_mode) {
    parts.push("Shadow mode är på — badet följer Eco Pak:s interna schema tills autostyrning aktiveras.");
  }
  return parts.join(" ");
}

export function filterSchedulePanelCopy(control: SpaControlConfig | null): {
  subtitle: string;
  checklist: string[];
  warning: string | null;
} {
  if (!control) {
    return {
      subtitle: "Optimerat med EMIC",
      checklist: ["Smart filterplanering"],
      warning: null,
    };
  }

  const window = `${control.allowed_window_start ?? "07:00"}–${control.allowed_window_end ?? "22:00"}`;
  const cycleHours = Math.max(1, Math.round(control.filter_duration_minutes / 60));
  const cycles = `${control.filter_cycles_per_day}×${cycleHours} h filter/dygn`;
  const warning = fixedScheduleWarningSv(control);

  if (control.strategy === "FIXED_SCHEDULE") {
    const fixed =
      control.fixed_schedule_start && control.fixed_schedule_end
        ? `${control.fixed_schedule_start}–${control.fixed_schedule_end}`
        : null;
    return {
      subtitle: fixed ? "Eco Pak styr tiderna inom fast fönster" : "Fast schema ofullständigt",
      checklist: fixed
        ? [
            `Fast fönster: ${fixed}`,
            cycles,
            "EMIC flyttar inte schemat",
            control.shadow_mode ? "Shadow mode — ingen autostyrning" : "Eco Pak sköter filtercyklerna",
          ]
        : [
            `Tillåtet fönster: ${window}`,
            cycles,
            "Saknar fast start/slut — öppna schema",
            control.shadow_mode ? "Shadow mode aktivt" : "Konfigurera under Visa schema",
          ],
      warning,
    };
  }

  if (control.strategy === "SOLAR_ONLY") {
    return {
      subtitle: "Prioriterar solel",
      checklist: [
        `Fönster: ${window}`,
        cycles,
        "Ren solenergi prioriterad",
        control.filter_optimization_enabled ? "EMIC väljer bästa soltimmar" : "Eco Pak internt schema",
      ],
      warning: null,
    };
  }

  if (control.strategy === "CHEAPEST") {
    return {
      subtitle: "Prioriterar lägsta elpris",
      checklist: [
        `Fönster: ${window}`,
        cycles,
        "Undviker höga elpriser",
        control.filter_optimization_enabled ? "EMIC väljer billigaste timmar" : "Eco Pak internt schema",
      ],
      warning: null,
    };
  }

  return {
    subtitle: "Optimerat med EMIC",
    checklist: [
      `Fönster: ${window}`,
      cycles,
      "Sol, pris och deadline balanserat",
      control.filter_optimization_enabled ? "Automatisk optimering" : "Eco Pak internt schema",
    ],
    warning: null,
  };
}

export function strategyLabelSv(strategy: string | null | undefined): string {
  if (!strategy) return "—";
  const known = SPA_STRATEGY_OPTIONS.find((option) => option.id === strategy);
  if (known) return known.label;
  const key = strategy.toLowerCase();
  if (key.includes("eco")) return "Eco";
  if (key.includes("smart")) return "Smart";
  if (key.includes("fixed")) return "Fast";
  return strategy;
}

export interface SpaSensorRow {
  label: string;
  value: string;
  group: "bad" | "effekt" | "system";
}

export function buildSensorRows(status: SpaStatus, health: SpaHealth | null): SpaSensorRow[] {
  const rows: SpaSensorRow[] = [
    {
      label: "Vattentemperatur",
      value: status.water_temperature_c != null ? `${status.water_temperature_c.toFixed(1)} °C` : "—",
      group: "bad",
    },
    {
      label: "Måltemperatur",
      value: status.set_temperature_c != null ? `${status.set_temperature_c.toFixed(1)} °C` : "—",
      group: "bad",
    },
    {
      label: "Värmare",
      value: isHeaterLive(status) ? "På" : "Av",
      group: "bad",
    },
    {
      label: "Filter",
      value: status.filter_status ?? "—",
      group: "bad",
    },
    {
      label: "Filtercykel",
      value: isFilterRunning(status) ? "Aktiv" : "Vilar",
      group: "bad",
    },
    {
      label: "UV-rening",
      value: isUvActive(status) ? "På" : "Av",
      group: "bad",
    },
    {
      label: "Pump",
      value: status.pump_label || "—",
      group: "bad",
    },
    {
      label: "Spa online",
      value: status.online ? "Ja" : "Nej",
      group: "bad",
    },
    {
      label: "Total effekt",
      value: formatKwFromW(status.current_power_w),
      group: "effekt",
    },
    {
      label: "Datakvalitet",
      value: status.data_quality,
      group: "effekt",
    },
  ];

  for (const row of buildComponentRows(status)) {
    rows.push({
      label: row.label,
      value: `${formatKwFromW(row.powerW)} · ${row.status}`,
      group: "effekt",
    });
  }

  if (health) {
    rows.push(
      { label: "API-status", value: health.api_status, group: "system" },
      { label: "Spa-status", value: health.spa_status, group: "system" },
      { label: "Polling", value: health.polling_status, group: "system" },
      { label: "Samples 24 h", value: String(health.samples_last_24h), group: "system" },
      { label: "Intervall 24 h", value: String(health.intervals_last_24h), group: "system" },
      { label: "Sample-energi 24 h", value: formatKwh(health.sample_energy_kwh_24h, 2), group: "system" },
    );
    if (health.last_error) {
      rows.push({ label: "Senaste fel", value: health.last_error, group: "system" });
    }
  }

  if (status.errors.length > 0) {
    rows.push({ label: "Fel", value: status.errors.join(", "), group: "system" });
  }

  return rows;
}

export function integrationLabelSv(dataSource: string): string {
  if (dataSource.includes("ARCTIC")) return "Eco Pak";
  return dataSource;
}

export function filterMinutesRemaining(
  status: SpaStatus,
  plan: SpaPlan | null,
  control: SpaControlConfig | null,
): number | null {
  if (!isFilterRunning(status, plan)) return null;
  const duration = control?.filter_duration_minutes ?? 60;
  const progress = filterProgressPct(status, plan, control);
  if (progress <= 0) return duration;
  return Math.max(1, Math.round(((100 - progress) / 100) * duration));
}

export function nextCycleLabel(plan: SpaPlan | null): string {
  if (!plan?.next_cleaning_start) return "—";
  return new Date(plan.next_cleaning_start).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function parsePumpLabel(pumpLabel: string): { index: number; state: string } | null {
  const match = pumpLabel.match(/Pump\s*(\d+)\s*:\s*(.+)/i);
  if (!match) return null;
  return { index: Number(match[1]), state: match[2].trim() };
}

function pumpStateSv(state: string, powerW: number): string {
  if (powerW <= 0 || /^off|av$/i.test(state)) return "Av";
  if (/high|hög/i.test(state)) return "Hög";
  if (/low|låg/i.test(state)) return "Låg";
  return "På";
}

function normalizeBreakdownKey(key: string): string {
  return key.toLowerCase().replace(/[\s_-]+/g, "");
}

export function buildComponentRows(status: SpaStatus): SpaComponentRow[] {
  const breakdown = status.power_breakdown ?? {};
  const byKey = new Map<string, number>();
  for (const [key, watts] of Object.entries(breakdown)) {
    byKey.set(normalizeBreakdownKey(key), watts);
  }

  const pumpRows: SpaComponentRow[] = [1, 2, 3].map((index) => {
    const watts =
      byKey.get(`pump${index}`) ??
      byKey.get(`pump${index}w`) ??
      0;
    const parsed = parsePumpLabel(status.pump_label);
    const state = parsed?.index === index ? parsed.state : watts > 0 ? "On" : "Off";
    return {
      id: `pump-${index}`,
      label: `Pump ${index}`,
      powerW: watts,
      status: pumpStateSv(state, watts >= MIN_PUMP_LOAD_W ? watts : 0),
    };
  });

  const heaterW = byKey.get("heater") ?? byKey.get("värmare") ?? 0;
  const circulationW = byKey.get("circulation") ?? byKey.get("cirkulation") ?? byKey.get("pump4") ?? 0;
  const blowerW = byKey.get("blower") ?? byKey.get("blower1") ?? 0;
  const heaterLive = isHeaterLive(status) && heaterW >= MIN_HEATER_LOAD_W;

  return [
    ...pumpRows,
    {
      id: "heater",
      label: "Värmare",
      powerW: heaterW,
      status: heaterLive ? "På" : "Av",
      detail:
        status.set_temperature_c != null ? `${status.set_temperature_c.toFixed(0)}°C` : undefined,
    },
    {
      id: "circulation",
      label: "Cirkulation",
      powerW: circulationW,
      status: circulationW >= MIN_PUMP_LOAD_W ? "På" : "Av",
    },
    {
      id: "blower",
      label: "Blower",
      powerW: blowerW,
      status: blowerW >= MIN_PUMP_LOAD_W ? "På" : "Av",
    },
  ];
}

export function breakdownShares(status: SpaStatus): Record<string, number> {
  const rows = buildComponentRows(status);
  const total = rows.reduce((sum, row) => sum + row.powerW, 0);
  if (total <= 0) {
    return { heater: 0.55, pumps: 0.35, circulation: 0.08, blower: 0.02 };
  }
  const pumps = rows.filter((r) => r.id.startsWith("pump")).reduce((s, r) => s + r.powerW, 0);
  const heater = rows.find((r) => r.id === "heater")?.powerW ?? 0;
  const circulation = rows.find((r) => r.id === "circulation")?.powerW ?? 0;
  const blower = rows.find((r) => r.id === "blower")?.powerW ?? 0;
  return {
    heater: heater / total,
    pumps: pumps / total,
    circulation: circulation / total,
    blower: blower / total,
  };
}

export function formatCostKr(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatSekAmount(value).label.replace("kr", "kr").replace(/\s/g, " ");
}

export function formatKwh(value: number | null | undefined, digits = 1): string {
  if (value == null) return "—";
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: digits })} kWh`;
}

export function formatKwFromW(watts: number | null | undefined): string {
  if (watts == null) return "—";
  return `${(watts / 1000).toLocaleString("sv-SE", { maximumFractionDigits: 2 })} kW`;
}

export function tempStable(status: SpaStatus): boolean {
  if (status.water_temperature_c == null || status.set_temperature_c == null) return false;
  return Math.abs(status.water_temperature_c - status.set_temperature_c) <= 0.5;
}

export function buildInsights(
  today: SpaEnergyPeriod | null,
  month: SpaEnergyPeriod | null,
  plan: SpaPlan | null,
  status: SpaStatus,
): Array<{ tone: "ok" | "warn" | "info"; text: string }> {
  const insights: Array<{ tone: "ok" | "warn" | "info"; text: string }> = [];
  if (today?.own_energy_pct != null && today.own_energy_pct >= 50) {
    insights.push({
      tone: "ok",
      text: `Spaet har använt ${Math.round(today.own_energy_pct)}% ren solenergi idag. Bra jobbat! Fortsätt så.`,
    });
  } else if (plan?.explanation_sv) {
    insights.push({ tone: "info", text: plan.explanation_sv });
  }
  if (today?.max_power_w != null && today.max_power_w > 0) {
    const kw = (today.max_power_w / 1000).toLocaleString("sv-SE", { maximumFractionDigits: 1 });
    insights.push({
      tone: "warn",
      text: `Toppeffekt idag: ${kw} kW. Vid uppvärmning.`,
    });
  }
  if (month?.actual_cost_sek != null) {
    insights.push({
      tone: "info",
      text: `Månadskostnad: ${formatCostKr(month.actual_cost_sek)}.`,
    });
  }
  if (insights.length === 0 && status.online) {
    insights.push({ tone: "info", text: "Spaet är online och rapporterar normalt." });
  }
  return insights.slice(0, 3);
}
