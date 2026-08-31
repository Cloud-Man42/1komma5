import type { DashboardVehicleSection } from "@/lib/api";
import { DashboardSection, Metric, StatusBadge } from "@/components/dashboard";

function qualityTone(quality: string | null | undefined): "success" | "warning" | "neutral" {
  if (quality === "LIVE" || quality === "MEASURED") return "success";
  if (quality === "STALE" || quality === "ESTIMATED") return "warning";
  return "neutral";
}

export function VehicleChargingWidget({ vehicle }: { vehicle: DashboardVehicleSection | null }) {
  if (!vehicle?.available) {
    return (
      <DashboardSection title="Mercedes EQE" subtitle={vehicle?.unavailable_reason ?? "Ingen fordonsdata"}>
        <p className="dashboard-muted">Fordonsintegrationen är inte tillgänglig.</p>
      </DashboardSection>
    );
  }

  const charging = vehicle.mode === "charging" || vehicle.is_charging;
  const title = vehicle.display_name ?? "Mercedes EQE";

  return (
    <DashboardSection
      title={title}
      subtitle={charging ? "Laddar" : "Parkerad"}
      action={<StatusBadge label={charging ? "Laddar" : "Parkerad"} tone={charging ? "success" : "neutral"} />}
      data-testid="vehicle-charging-widget"
    >
      <div className="dashboard-metric-row">
        <Metric label="SoC" value={vehicle.state_of_charge_percent != null ? `${Math.round(vehicle.state_of_charge_percent)}%` : "—"} />
        <Metric label="Räckvidd" value={vehicle.electric_range_km != null ? `${Math.round(vehicle.electric_range_km)} km` : "—"} />
        {charging ? (
          <Metric label="Effekt" value={vehicle.charging_power_kw != null ? `${vehicle.charging_power_kw.toFixed(1)} kW` : "—"} />
        ) : null}
      </div>
      {vehicle.location_name ? (
        <p className="dashboard-muted">Plats: {vehicle.location_name}{vehicle.charging_type ? ` · ${vehicle.charging_type}` : ""}</p>
      ) : null}
      {charging && vehicle.session_energy_kwh != null ? (
        <Metric label="Session" value={`${vehicle.session_energy_kwh.toFixed(1)} kWh`} />
      ) : null}
      {vehicle.freshness_label ? (
        <StatusBadge label={vehicle.freshness_label} tone={qualityTone(vehicle.data_quality ?? vehicle.freshness_label)} />
      ) : null}
    </DashboardSection>
  );
}
