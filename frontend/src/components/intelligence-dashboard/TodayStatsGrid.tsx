import type { DashboardTodaySection } from "@/lib/api";
import { formatEnergy, formatMoney } from "@/lib/format";
import { yesterdayComparisonLabel } from "./todayComparisonHelpers";

const STATS = [
  {
    key: "produced",
    label: "Producerat",
    icon: "☀",
    tone: "solar",
    field: "produced_kwh" as const,
    yesterdayField: "produced_kwh_yesterday" as const,
  },
  {
    key: "consumed",
    label: "Förbrukat",
    icon: "⚙",
    tone: "house",
    field: "consumed_kwh" as const,
    yesterdayField: "consumed_kwh_yesterday" as const,
  },
  {
    key: "imported",
    label: "Köpt från nät",
    icon: "⌂",
    tone: "battery",
    field: "imported_kwh" as const,
    yesterdayField: "imported_kwh_yesterday" as const,
  },
  {
    key: "exported",
    label: "Sålt till nät",
    icon: "⌂",
    tone: "grid",
    field: "exported_kwh" as const,
    yesterdayField: "exported_kwh_yesterday" as const,
  },
  {
    key: "cost",
    label: "Energikostnad",
    icon: "◎",
    tone: "solar",
    field: "energy_cost_sek" as const,
    yesterdayField: "energy_cost_sek_yesterday" as const,
    money: true,
  },
  {
    key: "savings",
    label: "Besparing",
    icon: "◎",
    tone: "grid",
    field: "savings_sek" as const,
    yesterdayField: "savings_sek_yesterday" as const,
    money: true,
  },
];

export function TodayStatsGrid({ today }: { today: DashboardTodaySection | null }) {
  if (!today) return null;

  return (
    <section className="idash-panel idash-today-panel">
      <h2 className="idash-panel-title">IDAG</h2>
      <div className="idash-today-grid">
        {STATS.map((stat) => {
          const raw = today[stat.field];
          const yesterdayRaw = today[stat.yesterdayField];
          const value =
            raw == null
              ? "—"
              : stat.money
                ? formatMoney(raw as number)
                : formatEnergy(raw as number);
          const comparison = yesterdayComparisonLabel(raw as number | null, yesterdayRaw as number | null);
          return (
            <div key={stat.key} className={`idash-today-stat idash-today-stat-${stat.tone}`}>
              <span className="idash-today-icon" aria-hidden="true">
                {stat.icon}
              </span>
              <div>
                <p className="idash-today-label">{stat.label}</p>
                <p className="idash-today-value">{value}</p>
                {comparison ? <p className="idash-today-yesterday muted">{comparison}</p> : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
