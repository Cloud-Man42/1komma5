"use client";

import { useCallback, useEffect, useState } from "react";
import {
  EnergyReasoning,
  VehicleChargeSession,
  VehicleIntegrationStatus,
  VehicleListItem,
  fetchCurrentVehicleChargeSession,
  fetchEnergyReasoning,
  fetchVehicleChargeSessions,
  fetchVehicleIntegrationStatus,
  fetchVehicles,
} from "@/lib/api";
import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";

export function useVehicleDashboardData(siteSlug: string) {
  const refreshSeconds = useDashboardRefreshSeconds();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vehicle, setVehicle] = useState<VehicleListItem | null>(null);
  const [session, setSession] = useState<VehicleChargeSession | null>(null);
  const [sessions, setSessions] = useState<VehicleChargeSession[]>([]);
  const [integration, setIntegration] = useState<VehicleIntegrationStatus | null>(null);
  const [reasoning, setReasoning] = useState<EnergyReasoning | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<number | null>(null);

  const reload = useCallback(async () => {
    try {
      const [vehiclesRes, integrationRes] = await Promise.all([
        fetchVehicles(siteSlug),
        fetchVehicleIntegrationStatus(siteSlug),
      ]);
      setIntegration(integrationRes);
      const primary = vehiclesRes.vehicles.find((v) => v.enabled) ?? vehiclesRes.vehicles[0] ?? null;
      setVehicle(primary);

      if (primary) {
        const [sessionList, current] = await Promise.all([
          fetchVehicleChargeSessions(siteSlug, primary.id).catch(() => ({ sessions: [] as VehicleChargeSession[] })),
          fetchCurrentVehicleChargeSession(siteSlug, primary.id).catch(() => null),
        ]);
        setSessions(sessionList.sessions);
        setSession(current);

        const chargerId = primary.halo_correlation?.charger_id;
        if (chargerId != null) {
          try {
            const reasoningRes = await fetchEnergyReasoning(siteSlug, chargerId);
            setReasoning(reasoningRes);
          } catch {
            setReasoning(null);
          }
        } else {
          setReasoning(null);
        }
      } else {
        setSession(null);
        setSessions([]);
        setReasoning(null);
      }

      setError(null);
      setLastLoadedAt(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda fordonsdata");
    } finally {
      setLoading(false);
    }
  }, [siteSlug]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (refreshSeconds <= 0) return;
    const id = window.setInterval(() => void reload(), refreshSeconds * 1000);
    return () => window.clearInterval(id);
  }, [reload, refreshSeconds]);

  return {
    loading,
    error,
    vehicle,
    session,
    sessions,
    integration,
    reasoning,
    lastLoadedAt,
    reload,
    refreshSeconds,
    commandsEnabled: integration?.commands_enabled ?? false,
    integrationEnabled: integration?.enabled ?? false,
  };
}
