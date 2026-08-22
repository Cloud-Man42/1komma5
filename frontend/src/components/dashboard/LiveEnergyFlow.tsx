import { DashboardLiveSection, Reading } from "@/lib/api";
import { formatPower, formatPercent } from "@/lib/format";
import { EnergyFlowDiagram } from "@/components/EnergyFlowDiagram";
import { Icon } from "@/components/dashboard/Icon";

function liveStatusItems(live: DashboardLiveSection) {
  const items: string[] = [];
  if ((live.solar_production_w ?? 0) >= 25) {
    items.push(`Producerar ${formatPower(live.solar_production_w)}`);
  }
  if ((live.grid_export_w ?? 0) >= 25) {
    items.push(`Säljer ${formatPower(live.grid_export_w)}`);
  } else if ((live.grid_import_w ?? 0) >= 25) {
    items.push(`Köper ${formatPower(live.grid_import_w)}`);
  }
  if (live.battery_direction === "charging") {
    items.push(`Batteri laddar ${formatPower(live.battery_power_w)}`);
  } else if (live.battery_direction === "discharging") {
    items.push(`Batteri urladdar ${formatPower(Math.abs(live.battery_power_w ?? 0))}`);
  } else if (live.battery_soc_pct != null) {
    items.push(`Batteri ${formatPercent(live.battery_soc_pct)}`);
  }
  if ((live.ev_power_w ?? 0) >= 25) {
    items.push(`Laddbox ${formatPower(live.ev_power_w)}`);
  }
  return items;
}

export function LiveEnergyFlow({
  siteSlug,
  live,
  reading,
  evPowerW,
}: {
  siteSlug: string;
  live: DashboardLiveSection | null;
  reading: Reading | null;
  evPowerW?: number;
}) {
  if (!reading) {
    return null;
  }

  const items = live ? liveStatusItems(live) : [];

  return (
    <div className="dashboard-surface">
      <EnergyFlowDiagram
        reading={reading}
        size="full"
        siteSlug={siteSlug}
        evPowerW={evPowerW ?? live?.ev_power_w ?? 0}
      />
      {items.length > 0 && (
        <div className="live-status-row" aria-label="Live status">
          {items.map((item) => (
            <span key={item} className="live-status-item">
              <Icon name="sun" />
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
