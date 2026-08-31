import type {
  AggregatedReading,
  DashboardLiveSection,
  DashboardTodaySection,
  PeakReading,
  Reading,
} from "@/lib/api";
import { gridFlowState, normalizeFlowValues, readingToFlowValues } from "@/lib/energyFlow";
import { readingTimestamp } from "@/lib/chartTime";

export { readingTimestamp } from "@/lib/chartTime";

export type HistoryBucketMinutes = 5 | 15 | 60;

export interface EnergyFlowChartPoint {
  label: string;
  sortKey: number;
  solarKw: number;
  consumptionKw: number;
  batteryChargeKw: number;
  batteryDischargeKw: number;
  netKw: number;
  socPct: number | null;
}

export interface EnergyBalanceSlice {
  id: "exported" | "imported" | "selfUsed";
  label: string;
  kwh: number;
  pct: number;
  color: string;
}

export interface EnergyLiveMetrics {
  solarW: number;
  consumptionW: number;
  batteryW: number;
  batterySocPct: number | null;
  batteryDirection: "charging" | "discharging" | "idle";
  gridNetW: number;
  gridExportW: number;
  gridImportW: number;
}

export interface EnergyTodayMetrics {
  producedKwh: number;
  consumedKwh: number;
  importedKwh: number;
  exportedKwh: number;
  batteryChargeKwh: number;
  batteryDischargeKwh: number;
  surplusKwh: number;
}

export function formatEnergyKwh(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: digits, minimumFractionDigits: digits })} kWh`;
}

export function formatEnergyKw(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1000) return `${(value / 1000).toFixed(2)} kW`;
  return `${Math.round(value)} W`;
}

export function integrateBatteryKwh(readings: (Reading | AggregatedReading)[]): {
  chargeKwh: number;
  dischargeKwh: number;
} {
  if (readings.length < 2) return { chargeKwh: 0, dischargeKwh: 0 };
  let chargeKwh = 0;
  let dischargeKwh = 0;
  for (let i = 1; i < readings.length; i += 1) {
    const prev = new Date(readingTimestamp(readings[i - 1])).getTime();
    const curr = new Date(readingTimestamp(readings[i])).getTime();
    const hours = Math.max(0, (curr - prev) / 3_600_000);
    const power = readings[i].battery_power_w ?? 0;
    if (power > 0) chargeKwh += (power * hours) / 1000;
    else dischargeKwh += (Math.abs(power) * hours) / 1000;
  }
  return { chargeKwh, dischargeKwh };
}

export function buildLiveMetrics(live: DashboardLiveSection | null | undefined): EnergyLiveMetrics {
  const solarW = live?.solar_production_w ?? 0;
  const consumptionW = live?.consumption_w ?? 0;
  const batteryW = live?.battery_power_w ?? 0;
  const normalized = normalizeFlowValues(
    readingToFlowValues({
      recorded_at: "",
      solar_production_w: solarW,
      consumption_w: consumptionW,
      grid_import_w: live?.grid_import_w ?? 0,
      grid_export_w: live?.grid_export_w ?? 0,
      battery_soc_pct: live?.battery_soc_pct ?? 0,
      battery_power_w: batteryW,
    }),
  );
  const grid = gridFlowState(normalized.gridImportW, normalized.gridExportW);
  const direction =
    live?.battery_direction ??
    (batteryW > 25 ? "charging" : batteryW < -25 ? "discharging" : "idle");
  return {
    solarW,
    consumptionW,
    batteryW,
    batterySocPct: live?.battery_soc_pct ?? null,
    batteryDirection: direction,
    gridNetW: -grid.signedW,
    gridExportW: grid.exportW,
    gridImportW: grid.importW,
  };
}

export function buildTodayMetrics(
  today: DashboardTodaySection | null | undefined,
  batteryFromHistory: { chargeKwh: number; dischargeKwh: number },
): EnergyTodayMetrics {
  const producedKwh = today?.produced_kwh ?? 0;
  const consumedKwh = today?.consumed_kwh ?? 0;
  const importedKwh = today?.imported_kwh ?? 0;
  const exportedKwh = today?.exported_kwh ?? 0;
  return {
    producedKwh,
    consumedKwh,
    importedKwh,
    exportedKwh,
    batteryChargeKwh: batteryFromHistory.chargeKwh,
    batteryDischargeKwh: batteryFromHistory.dischargeKwh,
    surplusKwh: exportedKwh - importedKwh,
  };
}

export function buildEnergyBalance(today: EnergyTodayMetrics): {
  centerLabel: string;
  centerValue: string;
  slices: EnergyBalanceSlice[];
} {
  const exported = Math.max(0, today.exportedKwh);
  const imported = Math.max(0, today.importedKwh);
  const selfUsed = Math.max(0, today.producedKwh - exported);
  const total = exported + imported + selfUsed || 1;
  const surplus = today.surplusKwh;
  const centerValue =
    surplus >= 0
      ? `${surplus.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`
      : `${Math.abs(surplus).toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`;
  const centerLabel = surplus >= 0 ? "Överskott" : "Underskott";
  return {
    centerLabel,
    centerValue,
    slices: [
      { id: "exported", label: "Exporterat", kwh: exported, pct: (exported / total) * 100, color: "#4ade80" },
      { id: "imported", label: "Importerat", kwh: imported, pct: (imported / total) * 100, color: "#38bdf8" },
      { id: "selfUsed", label: "Egenanvänt", kwh: selfUsed, pct: (selfUsed / total) * 100, color: "#fbbf24" },
    ],
  };
}

export function buildFlowChartSeries(
  readings: (Reading | AggregatedReading)[],
  timezone = "Europe/Stockholm",
): EnergyFlowChartPoint[] {
  return readings
    .map((reading) => {
      const iso = readingTimestamp(reading);
      const date = new Date(iso);
      const label = date.toLocaleTimeString("sv-SE", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: timezone,
      });
      const battery = reading.battery_power_w ?? 0;
      const solarKw = (reading.solar_production_w ?? 0) / 1000;
      const consumptionKw = (reading.consumption_w ?? 0) / 1000;
      const batteryChargeKw = battery > 0 ? battery / 1000 : 0;
      const batteryDischargeKw = battery < 0 ? Math.abs(battery) / 1000 : 0;
      const netKw = solarKw - consumptionKw + (battery > 0 ? batteryChargeKw : -batteryDischargeKw);
      return {
        label,
        sortKey: date.getTime(),
        solarKw,
        consumptionKw,
        batteryChargeKw,
        batteryDischargeKw,
        netKw,
        socPct: reading.battery_soc_pct ?? null,
      };
    })
    .sort((a, b) => a.sortKey - b.sortKey);
}

export function buildSocSeries(readings: (Reading | AggregatedReading)[]): number[] {
  return readings.map((r) => r.battery_soc_pct ?? 0);
}

export function sparklineFromReadings(
  readings: (Reading | AggregatedReading)[],
  pick: (r: Reading | AggregatedReading) => number,
): number[] {
  return readings.map(pick);
}

export function peakSummary(peaks: PeakReading[]) {
  return {
    solar: Math.max(0, ...peaks.map((p) => p.solar_production_w)),
    consumption: Math.max(0, ...peaks.map((p) => p.consumption_w ?? 0)),
    charge: Math.max(0, ...peaks.map((p) => p.battery_charge_w)),
    discharge: Math.max(0, ...peaks.map((p) => p.battery_discharge_w)),
  };
}

export function exportEnergyCsv(
  readings: (Reading | AggregatedReading)[],
  filename = "energi-export.csv",
): void {
  if (typeof window === "undefined" || readings.length === 0) return;
  if (typeof URL.createObjectURL !== "function") return;
  const header = [
    "timestamp",
    "solar_production_w",
    "consumption_w",
    "grid_import_w",
    "grid_export_w",
    "battery_power_w",
    "battery_soc_pct",
  ];
  const rows = readings.map((r) =>
    [
      readingTimestamp(r),
      r.solar_production_w,
      r.consumption_w,
      r.grid_import_w,
      r.grid_export_w,
      r.battery_power_w,
      r.battery_soc_pct,
    ].join(","),
  );
  const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function formatPeakPeriod(value: string, period: "day" | "month" | "year"): string {
  if (period === "year") return value;
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("sv-SE", {
    year: "numeric",
    month: period === "month" ? "long" : "short",
    ...(period === "day" ? { day: "numeric" } : {}),
  }).format(new Date(year, month - 1, day ?? 1));
}

export function todayDateLabel(timezone = "Europe/Stockholm"): string {
  const now = new Date();
  const date = now.toLocaleDateString("sv-SE", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: timezone,
  });
  return `${date} Idag`;
}
