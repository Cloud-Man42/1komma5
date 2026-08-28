"use client";

import { FormEvent, useState } from "react";
import type { VehicleListItem } from "@/lib/api";
import {
  sendVehicleSetTargetSoc,
  startVehicleCharging,
  stopVehicleCharging,
} from "@/lib/api";
import { formatPercent } from "./vehicleDashboardHelpers";

type Props = {
  siteSlug: string;
  vehicle: VehicleListItem;
  commandsEnabled: boolean;
  onChanged: () => void;
};

export function VehicleActionsPanel({ siteSlug, vehicle, commandsEnabled, onChanged }: Props) {
  const [targetSoc, setTargetSoc] = useState(
    vehicle.target_soc_percent != null ? String(Math.round(vehicle.target_soc_percent)) : "80",
  );
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (action: string, fn: () => Promise<{ message: string }>) => {
    setBusy(action);
    setMessage(null);
    setError(null);
    try {
      const result = await fn();
      setMessage(result.message);
      onChanged();
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

  if (!commandsEnabled) {
    return (
      <section className="vdash-card vdash-actions-card" data-testid="vehicle-actions">
        <header className="vdash-card-header">
          <h2>FORDONSÅTGÄRDER</h2>
        </header>
        <p className="vdash-muted">Kommandon är avstängda. Aktivera under Konfiguration → Mercedes me.</p>
      </section>
    );
  }

  return (
    <section className="vdash-card vdash-actions-card" data-testid="vehicle-actions">
      <header className="vdash-card-header">
        <h2>FORDONSÅTGÄRDER</h2>
      </header>
      <ul className="vdash-action-list">
        <li>
          <form className="vdash-action-form" onSubmit={(e) => void onSetTarget(e)}>
            <label className="vdash-action-btn vdash-action-btn-form">
              <span>
                <strong>Sätt mål-SoC</strong>
                <small>Aktuellt: {formatPercent(vehicle.target_soc_percent)}</small>
              </span>
              <input
                type="number"
                min={30}
                max={100}
                value={targetSoc}
                onChange={(e) => setTargetSoc(e.target.value)}
                disabled={!vehicle.capabilities.can_set_target_soc || busy !== null}
                aria-label="Mål-SoC procent"
              />
            </label>
            <button
              type="submit"
              className="vdash-card-btn"
              disabled={!vehicle.capabilities.can_set_target_soc || busy !== null}
            >
              {busy === "target" ? "Skickar…" : "Skicka"}
            </button>
          </form>
        </li>
        <li>
          <button
            type="button"
            className="vdash-action-btn"
            disabled={!vehicle.capabilities.can_start_charging || busy !== null}
            onClick={() => run("start", () => startVehicleCharging(siteSlug, vehicle.id))}
          >
            <span>
              <strong>Starta laddning</strong>
              <small>Mercedes me-kommando</small>
            </span>
            <span className="vdash-chevron" aria-hidden="true">›</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            className="vdash-action-btn"
            disabled={!vehicle.capabilities.can_stop_charging || busy !== null}
            onClick={() => run("stop", () => stopVehicleCharging(siteSlug, vehicle.id))}
          >
            <span>
              <strong>Stoppa laddning</strong>
              <small>Mercedes me-kommando</small>
            </span>
            <span className="vdash-chevron" aria-hidden="true">›</span>
          </button>
        </li>
      </ul>
      {message ? <p className="vdash-action-msg vdash-action-msg-ok">{message}</p> : null}
      {error ? <p className="vdash-action-msg vdash-action-msg-err">{error}</p> : null}
    </section>
  );
}
