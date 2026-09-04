"use client";

import { useEffect, useState } from "react";
import {
  fetchEnergyBalance,
  fetchEvChargers,
  type EnergyBalanceSnapshot,
  type EvCharger,
} from "@/lib/api";

function statusLabel(status: string | null | undefined): string {
  switch ((status || "").toLowerCase()) {
    case "ok":
      return "Balanserad";
    case "warning":
      return "Avvikelse";
    case "critical":
      return "Kritisk avvikelse";
    default:
      return "Ingen data";
  }
}

export function EnergyBalanceQualityCard({ slug }: { slug: string }) {
  const [charger, setCharger] = useState<EvCharger | null>(null);
  const [balance, setBalance] = useState<EnergyBalanceSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchEvChargers(slug)
      .then((rows) => rows.find((row) => row.bridge_enabled) ?? rows[0] ?? null)
      .then((selected) => {
        if (!active) return null;
        setCharger(selected);
        if (!selected) {
          setBalance(null);
          return null;
        }
        return fetchEnergyBalance(slug, selected.id);
      })
      .then((payload) => {
        if (!active) return;
        setBalance(payload);
        setError(null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setBalance(null);
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  const flags = balance?.flags?.length ? balance.flags.join(", ") : null;

  return (
    <section className="idash-panel" data-testid="energy-balance-quality-card">
      <h2 className="idash-panel-title">Energibalans</h2>
      {error ? <p className="muted">{error}</p> : null}
      {!charger && !error ? <p className="muted">Ingen laddare konfigurerad.</p> : null}
      {charger ? (
        <>
          <p className="idash-balance-status">{statusLabel(balance?.status)}</p>
          {balance?.alignment_delta_seconds != null ? (
            <p className="muted">
              Tidsjustering: {Math.round(balance.alignment_delta_seconds)} s
            </p>
          ) : null}
          {flags ? <p className="muted">Flaggor: {flags}</p> : null}
        </>
      ) : null}
    </section>
  );
}
