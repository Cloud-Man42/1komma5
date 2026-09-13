import type { MultiSiteAggregate } from "@/lib/multiSiteApi";

function fmtKw(v: number | null | undefined, suffix = " kW"): string {
  if (v == null) return "—";
  return `${v.toFixed(1)}${suffix}`;
}

function fmtKwh(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(1)} kWh`;
}

export function OverviewKpiStrip({
  aggregate,
  partial,
}: {
  aggregate: MultiSiteAggregate;
  partial: boolean;
}) {
  const items = [
    { label: "Last nu", value: fmtKw(aggregate.consumptionPowerKw) },
    { label: "Sol nu", value: fmtKw(aggregate.solarPowerKw) },
    { label: "Batteri", value: fmtKw(aggregate.batteryChargePowerKw ?? aggregate.batteryDischargePowerKw) },
    { label: "Nät import", value: fmtKw(aggregate.gridImportPowerKw) },
    { label: "Nät export", value: fmtKw(aggregate.gridExportPowerKw) },
    { label: "Sol idag", value: fmtKwh(aggregate.solarTodayKwh) },
    { label: "Förbrukning idag", value: fmtKwh(aggregate.consumptionTodayKwh) },
    { label: "Import idag", value: fmtKwh(aggregate.gridImportTodayKwh) },
    { label: "Export idag", value: fmtKwh(aggregate.gridExportTodayKwh) },
    {
      label: "Batteri SoC",
      value: aggregate.batterySocPercent != null ? `${aggregate.batterySocPercent}%` : "—",
    },
  ];

  return (
    <div className="ms-kpi-grid">
      {items.map((item) => (
        <article key={item.label} className="ms-kpi-card">
          <span className="ms-kpi-label">{item.label}</span>
          <strong className="ms-kpi-value">{item.value}</strong>
          {partial ? <span className="ms-kpi-partial">Partiell data</span> : null}
        </article>
      ))}
    </div>
  );
}
