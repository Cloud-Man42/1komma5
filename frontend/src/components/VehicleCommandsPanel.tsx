"use client";

import { FormEvent, useState } from "react";

import {
  VehicleListItem,
  sendVehicleSetTargetSoc,
  startVehicleCharging,
  stopVehicleCharging,
} from "@/lib/api";

type Props = {
  siteSlug: string;
  vehicle: VehicleListItem;
  commandsEnabled: boolean;
};

export function VehicleCommandsPanel({ siteSlug, vehicle, commandsEnabled }: Props) {
  const [targetSoc, setTargetSoc] = useState(
    vehicle.target_soc_percent != null ? String(Math.round(vehicle.target_soc_percent)) : "80",
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  if (!commandsEnabled) {
    return (
      <div className="diagnostics-subpanel" data-testid="vehicle-commands-panel">
        <h4>Mercedes-kommandon</h4>
        <p className="muted">Kommandon är avstängda. Aktivera under Konfiguration → Mercedes me.</p>
      </div>
    );
  }

  const run = async (action: string, fn: () => Promise<{ message: string }>) => {
    setBusy(action);
    setMessage(null);
    setError(null);
    try {
      const result = await fn();
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kommandot misslyckades");
    } finally {
      setBusy(null);
    }
  };

  const onSetTarget = async (event: FormEvent) => {
    event.preventDefault();
    const value = Number(targetSoc);
    if (!Number.isFinite(value) || value < 30 || value > 100) {
      setError("Mål-SoC måste vara mellan 30 och 100");
      return;
    }
    await run("target", () => sendVehicleSetTargetSoc(siteSlug, vehicle.id, value));
  };

  return (
    <div className="diagnostics-subpanel" data-testid="vehicle-commands-panel">
      <h4>Mercedes-kommandon</h4>
      <p className="muted">
        Skickar protobuf-kommandon till Mercedes. Verifiera mot EQE innan produktionsbruk.
      </p>
      <div className="form-grid">
        <form onSubmit={onSetTarget} className="form-grid">
          <label className="form-field">
            <span>Mål-SoC (%)</span>
            <input
              type="number"
              min={30}
              max={100}
              value={targetSoc}
              onChange={(e) => setTargetSoc(e.target.value)}
              disabled={!vehicle.capabilities.can_set_target_soc || busy !== null}
            />
          </label>
          <button
            type="submit"
            className="btn-secondary"
            disabled={!vehicle.capabilities.can_set_target_soc || busy !== null}
          >
            Sätt mål-SoC
          </button>
        </form>
        <div className="form-actions">
          <button
            type="button"
            className="btn-secondary"
            disabled={!vehicle.capabilities.can_start_charging || busy !== null}
            onClick={() => run("start", () => startVehicleCharging(siteSlug, vehicle.id))}
          >
            Starta laddning
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={!vehicle.capabilities.can_stop_charging || busy !== null}
            onClick={() => run("stop", () => stopVehicleCharging(siteSlug, vehicle.id))}
          >
            Stoppa laddning
          </button>
        </div>
      </div>
      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
