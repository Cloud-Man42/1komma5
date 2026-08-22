import { DashboardEvSection, DashboardLiveSection, DashboardSolarSection } from "@/lib/api";
import { formatEnergy, formatPercent, formatPower } from "@/lib/format";
import { EmptyState } from "@/components/dashboard";

export function BatteryCard({ live }: { live: DashboardLiveSection | null }) {
  if (!live || live.battery_soc_pct == null) {
    return (
      <div className="detail-card">
        <h3 className="detail-card-title">Batteri</h3>
        <EmptyState title="Ingen batteridata" />
      </div>
    );
  }

  const directionLabel =
    live.battery_direction === "charging"
      ? "Laddar"
      : live.battery_direction === "discharging"
        ? "Urladdar"
        : "Vilar";

  return (
    <div className="detail-card">
      <h3 className="detail-card-title">Batteri</h3>
      <p className="detail-card-value">{formatPercent(live.battery_soc_pct)}</p>
      <p className="detail-card-meta">
        {directionLabel}
        {live.battery_power_w != null ? ` · ${formatPower(Math.abs(live.battery_power_w))}` : ""}
      </p>
    </div>
  );
}

export function EvCard({ ev }: { ev: DashboardEvSection | null }) {
  if (!ev?.available) {
    return (
      <div className="detail-card">
        <h3 className="detail-card-title">Laddbox</h3>
        <EmptyState title="Ingen laddbox ansluten" />
      </div>
    );
  }

  return (
    <div className="detail-card">
      <h3 className="detail-card-title">Laddbox</h3>
      <p className="detail-card-value">
        {ev.charging ? formatPower(ev.power_w) : ev.display_status_sv ?? "Väntar"}
      </p>
      <p className="detail-card-meta">
        {ev.charging_mode ? `Läge: ${ev.charging_mode}` : "Smart laddning"}
      </p>
    </div>
  );
}

export function SolarSummaryCard({ solar }: { solar: DashboardSolarSection | null }) {
  if (!solar || solar.unavailable_reason) {
    return (
      <div className="detail-card">
        <h3 className="detail-card-title">Solprognos</h3>
        <EmptyState title="Solprognos otillgänglig" text={solar?.unavailable_reason ?? undefined} />
      </div>
    );
  }

  return (
    <div className="detail-card">
      <h3 className="detail-card-title">Solprognos</h3>
      <p className="detail-card-value">{formatEnergy(solar.expected_today_kwh)}</p>
      <p className="detail-card-meta">
        Återstår {formatEnergy(solar.remaining_kwh)}
        {solar.confidence_pct != null ? ` · ${formatPercent(solar.confidence_pct)} säkerhet` : ""}
      </p>
    </div>
  );
}
