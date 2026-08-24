"use client";

import { useCallback, useEffect, useState } from "react";

import {
  VehicleChargeSession,
  VehicleIntegrationStatus,
  VehicleListItem,
  fetchCurrentVehicleChargeSession,
  fetchVehicleChargeSessions,
  fetchVehicleIntegrationStatus,
  fetchVehicles,
} from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

import { MercedesIntegrationPanel } from "@/components/MercedesIntegrationPanel";
import { VehicleCommandsPanel } from "@/components/VehicleCommandsPanel";

function formatPercent(value: number | null | undefined): string {
  if (value == null) return "Ej tillgängligt";
  return `${value.toFixed(0)} %`;
}

function formatKm(value: number | null | undefined): string {
  if (value == null) return "Ej tillgängligt";
  return `${value.toFixed(0)} km`;
}

function formatKw(value: number | null | undefined): string {
  if (value == null) return "Ej tillgängligt";
  return `${value.toFixed(1)} kW`;
}

function freshnessClass(label: string): string {
  if (label === "LIVE") return "badge badge-success";
  if (label === "UPPSKATTAT") return "badge badge-warning";
  if (label === "INAKTUELL") return "badge badge-warning";
  return "badge badge-muted";
}

function capabilityLabel(value: boolean | null | undefined): string {
  if (value === true) return "Ja";
  if (value === false) return "Ej tillgängligt";
  return "Ej tillgängligt";
}

function VehicleCard({ vehicle }: { vehicle: VehicleListItem }) {
  return (
    <div className="spa-kpi-grid" data-testid={`vehicle-card-${vehicle.id}`}>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{formatPercent(vehicle.state_of_charge_percent)}</p>
        <p className="spa-kpi-label">State of charge</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{formatPercent(vehicle.target_soc_percent)}</p>
        <p className="spa-kpi-label">Mål-SoC</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{formatKm(vehicle.electric_range_km)}</p>
        <p className="spa-kpi-label">Räckvidd</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{vehicle.is_plugged_in == null ? "Ej tillgängligt" : vehicle.is_plugged_in ? "Ja" : "Nej"}</p>
        <p className="spa-kpi-label">Ansluten</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{vehicle.is_charging == null ? "Ej tillgängligt" : vehicle.is_charging ? "Ja" : "Nej"}</p>
        <p className="spa-kpi-label">Laddar</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{formatKw(vehicle.charging_power_kw)}</p>
        <p className="spa-kpi-label">Laddeffekt</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">
          <span className={freshnessClass(vehicle.freshness_label)}>{vehicle.freshness_label}</span>
        </p>
        <p className="spa-kpi-label">Datastatus</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{vehicle.masked_vin || "—"}</p>
        <p className="spa-kpi-label">VIN</p>
      </div>
      <div className="spa-kpi">
        <p className="spa-kpi-value">{capabilityLabel(vehicle.capabilities.can_read_charging_power)}</p>
        <p className="spa-kpi-label">Laddeffekt (capability)</p>
      </div>
    </div>
  );
}

function formatKwh(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(2)} kWh`;
}

function formatSek(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(2)} kr`;
}

function VehicleSessionsPanel({
  siteSlug,
  vehicleId,
}: {
  siteSlug: string;
  vehicleId: number;
}) {
  const [sessions, setSessions] = useState<VehicleChargeSession[]>([]);
  const [current, setCurrent] = useState<VehicleChargeSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchVehicleChargeSessions(siteSlug, vehicleId),
      fetchCurrentVehicleChargeSession(siteSlug, vehicleId).catch(() => null),
    ])
      .then(([list, active]) => {
        setSessions(list.sessions);
        setCurrent(active);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda laddsessioner"));
  }, [siteSlug, vehicleId]);

  if (error) {
    return <p className="form-error">{error}</p>;
  }

  const displaySession = current ?? sessions.find((session) => session.status === "ACTIVE") ?? null;

  return (
    <div className="diagnostics-subpanel" data-testid="vehicle-charge-sessions">
      <h4>Laddsessioner</h4>
      {displaySession ? (
        <div className="diagnostics-grid">
          <div>
            <span className="muted">Status</span>
            <strong>{displaySession.status === "ACTIVE" ? "Pågår" : "Avslutad"}</strong>
          </div>
          <div>
            <span className="muted">Halo energi</span>
            <strong>{formatKwh(displaySession.halo_energy_kwh)}</strong>
          </div>
          <div>
            <span className="muted">SoC start → slut</span>
            <strong>
              {formatPercent(displaySession.start_soc)} → {formatPercent(displaySession.end_soc)}
            </strong>
          </div>
          <div>
            <span className="muted">Identifiering</span>
            <strong>
              {displaySession.identification_confidence == null
                ? "—"
                : `${Math.round(displaySession.identification_confidence * 100)} %`}
            </strong>
          </div>
          <div>
            <span className="muted">Sol direkt</span>
            <strong>{formatKwh(displaySession.energy_sources.solar_direct_kwh)}</strong>
          </div>
          <div>
            <span className="muted">Sol via batteri</span>
            <strong>{formatKwh(displaySession.energy_sources.solar_battery_kwh)}</strong>
          </div>
          <div>
            <span className="muted">Nät via batteri</span>
            <strong>{formatKwh(displaySession.energy_sources.grid_battery_kwh)}</strong>
          </div>
          <div>
            <span className="muted">Nät direkt</span>
            <strong>{formatKwh(displaySession.energy_sources.grid_direct_kwh)}</strong>
          </div>
          <div>
            <span className="muted">Kostnad</span>
            <strong>{formatSek(displaySession.actual_cost_sek)}</strong>
          </div>
          <div>
            <span className="muted">Besparing</span>
            <strong>{formatSek(displaySession.savings_sek)}</strong>
          </div>
        </div>
      ) : (
        <p className="muted">Ingen laddsession registrerad ännu.</p>
      )}
      {sessions.length > 1 && (
        <p className="muted">Historik: {sessions.length} sessioner sparade.</p>
      )}
    </div>
  );
}

export function VehiclePanel({ siteSlug }: { siteSlug: string }) {
  const [vehicles, setVehicles] = useState<VehicleListItem[]>([]);
  const [status, setStatus] = useState<VehicleIntegrationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refreshSeconds = useDashboardRefreshSeconds();

  const load = useCallback(async () => {
    try {
      const [vehicleList, integrationStatus] = await Promise.all([
        fetchVehicles(siteSlug),
        fetchVehicleIntegrationStatus(siteSlug),
      ]);
      setVehicles(vehicleList.vehicles);
      setStatus(integrationStatus);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda fordonsdata");
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), refreshSeconds * 1000);
    return () => clearInterval(timer);
  }, [load, refreshSeconds]);

  if (error && !status) {
    return <p className="form-error">{error}</p>;
  }

  if (!status) {
    return <p className="muted">Laddar fordonsintegration…</p>;
  }

  if (!status.enabled) {
    return (
      <section className="card diagnostics-panel" data-testid="vehicle-panel">
        <h3>Mercedes me</h3>
        <p className="muted">Fordonsintegrationen är inte aktiverad. Konfigurera under Konfiguration → Anläggningar.</p>
      </section>
    );
  }

  return (
    <section className="card diagnostics-panel" data-testid="vehicle-panel">
      <h3>{vehicles[0]?.display_name || "Mercedes me"}</h3>
      {vehicles.length === 0 ? (
        <p className="muted">Inga fordon hittades ännu. Kontrollera inloggning under Konfiguration.</p>
      ) : (
        vehicles.map((vehicle) => <VehicleCard key={vehicle.id} vehicle={vehicle} />)
      )}
      <MercedesIntegrationPanel siteSlug={siteSlug} status={status} />
      {vehicles[0]?.halo_correlation && (
        <div className="diagnostics-subpanel" data-testid="vehicle-halo-correlation">
          <h4>Halo-korrelation</h4>
          <div className="diagnostics-grid">
            <div>
              <span className="muted">Status</span>
              <strong>{vehicles[0].halo_correlation.status}</strong>
            </div>
            <div>
              <span className="muted">Confidence</span>
              <strong>{Math.round(vehicles[0].halo_correlation.confidence * 100)} %</strong>
            </div>
            <div>
              <span className="muted">Mercedes effekt</span>
              <strong>{formatKw(vehicles[0].halo_correlation.vehicle_power_kw)}</strong>
            </div>
            <div>
              <span className="muted">Halo effekt</span>
              <strong>{formatKw(vehicles[0].halo_correlation.halo_power_kw)}</strong>
            </div>
            <div className="diagnostics-span-all">
              <span className="muted">Notering</span>
              <strong>{vehicles[0].halo_correlation.notes}</strong>
            </div>
          </div>
        </div>
      )}
      {vehicles[0] && <VehicleSessionsPanel siteSlug={siteSlug} vehicleId={vehicles[0].id} />}
      {vehicles[0] && (
        <VehicleCommandsPanel
          siteSlug={siteSlug}
          vehicle={vehicles[0]}
          commandsEnabled={status.commands_enabled}
        />
      )}
    </section>
  );
}
