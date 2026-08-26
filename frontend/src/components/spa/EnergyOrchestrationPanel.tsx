"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EnergyOrchestration,
  EnergyOrchestrationLoad,
  fetchEnergyOrchestration,
  updateEnergyOrchestrationPriorities,
} from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function formatWindow(load: EnergyOrchestrationLoad): string {
  if (!load.window_start || !load.window_end) return "Ingen plan ännu";
  const start = new Date(load.window_start);
  const end = new Date(load.window_end);
  return `${start.toLocaleString("sv-SE", { hour: "2-digit", minute: "2-digit" })}–${end.toLocaleString("sv-SE", { hour: "2-digit", minute: "2-digit" })}`;
}

export function EnergyOrchestrationPanel({ siteSlug }: { siteSlug: string }) {
  const [data, setData] = useState<EnergyOrchestration | null>(null);
  const [priorities, setPriorities] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetchEnergyOrchestration(siteSlug);
      setData(response);
      setPriorities(Object.fromEntries(response.loads.map((item) => [item.load_id, item.priority])));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda energiordning");
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    if (!data) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await updateEnergyOrchestrationPriorities(
        siteSlug,
        data.loads.map((item) => ({ load_id: item.load_id, priority: priorities[item.load_id] ?? item.priority })),
      );
      setData(updated);
      setPriorities(Object.fromEntries(updated.loads.map((item) => [item.load_id, item.priority])));
      setMessage("Prioritering sparad");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara prioritering");
    } finally {
      setSaving(false);
    }
  }

  if (error && !data) {
    return (
      <section className="card" data-testid="energy-orchestration">
        <p className="form-error">{error}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="card" data-testid="energy-orchestration">
        <p className="muted">Laddar energiordning…</p>
      </section>
    );
  }

  if (data.loads.length === 0) {
    return (
      <section className="card" data-testid="energy-orchestration">
        <h3>Energiordning</h3>
        <p className="muted">Inga flexibla laster är aktiva på denna site.</p>
      </section>
    );
  }

  return (
    <section className="card" data-testid="energy-orchestration">
      <h3>Energiordning</h3>
      <p className="muted">Högre prioritet får solel och billig energi först. Lägre laster planeras kring reserverad kapacitet.</p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Last</th>
            <th>Prioritet</th>
            <th>Planerat fönster</th>
            <th>Beräknad kostnad</th>
          </tr>
        </thead>
        <tbody>
          {data.loads.map((item) => (
            <tr key={item.load_id}>
              <td>{item.name}</td>
              <td>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={priorities[item.load_id] ?? item.priority}
                  onChange={(e) =>
                    setPriorities((current) => ({
                      ...current,
                      [item.load_id]: Number(e.target.value),
                    }))
                  }
                />
              </td>
              <td>{formatWindow(item)}</td>
              <td>
                {item.expected_cost_sek != null ? formatSekAmount(item.expected_cost_sek).label : "—"}
                {item.dry_run ? " (Dry Run)" : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" className="btn-primary" disabled={saving} onClick={() => void handleSave()}>
        {saving ? "Sparar…" : "Spara prioritering"}
      </button>
      {message && <p className="form-success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
    </section>
  );
}
