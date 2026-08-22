"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EvChargingSession,
  EvChargingStats,
  fetchCurrentEvSession,
  fetchEvChargingSession,
  fetchEvChargingSessions,
  fetchEvChargingStats,
} from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

function formatKwh(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)} kWh`;
}

function formatTimeRange(start: string, end: string | null): string {
  const s = new Date(start);
  const e = end ? new Date(end) : null;
  const fmt = (d: Date) =>
    d.toLocaleString("sv-SE", { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" });
  if (!e) return fmt(s);
  return `${fmt(s)} → ${fmt(e)}`;
}

function EnergyMixBar({ sources, total }: { sources: EvChargingStats["energy_sources"]; total: number }) {
  if (total <= 0) return <p className="text-sm text-muted-foreground">Ingen ladddata ännu.</p>;
  const items = [
    { label: "Direkt sol", kwh: sources.solar_direct_kwh, color: "bg-amber-400" },
    { label: "Sol via batteri", kwh: sources.solar_battery_kwh, color: "bg-amber-300" },
    { label: "Nät via batteri", kwh: sources.grid_battery_kwh, color: "bg-sky-400" },
    { label: "Direkt nät", kwh: sources.grid_direct_kwh, color: "bg-slate-400" },
  ];
  return (
    <div className="space-y-2">
      {items.map((item) => {
        const pct = total > 0 ? (item.kwh / total) * 100 : 0;
        return (
          <div key={item.label}>
            <div className="flex justify-between text-sm">
              <span>{item.label}</span>
              <span>
                {item.kwh.toFixed(0)} kWh ({pct.toFixed(0)} %)
              </span>
            </div>
            <div className="h-2 rounded bg-muted">
              <div className={`h-2 rounded ${item.color}`} style={{ width: `${Math.min(100, pct)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function EvChargingAnalytics({ siteSlug, chargerId }: { siteSlug: string; chargerId: number }) {
  const [stats, setStats] = useState<EvChargingStats | null>(null);
  const [sessions, setSessions] = useState<EvChargingSession[]>([]);
  const [current, setCurrent] = useState<EvChargingSession | null>(null);
  const [selected, setSelected] = useState<EvChargingSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [monthStats, history, active] = await Promise.all([
        fetchEvChargingStats(siteSlug, chargerId, "month"),
        fetchEvChargingSessions(siteSlug, chargerId, 10),
        fetchCurrentEvSession(siteSlug, chargerId),
      ]);
      setStats(monthStats);
      setSessions(history);
      setCurrent(active);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte hämta laddstatistik");
    }
  }, [siteSlug, chargerId]);

  useEffect(() => {
    void load();
  }, [load]);

  const openSession = async (sessionId: number) => {
    const detail = await fetchEvChargingSession(siteSlug, chargerId, sessionId);
    setSelected(detail);
  };

  const latest = sessions[0] ?? current;

  return (
    <section className="mt-6 space-y-4 rounded-lg border p-4">
      <h3 className="text-lg font-semibold">EV-laddning — ekonomi</h3>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs text-muted-foreground">Laddat (30 d)</p>
            <p className="text-xl font-semibold">{formatKwh(stats.total_energy_kwh)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Kostnad</p>
            <p className="text-xl font-semibold">{formatSekAmount(stats.actual_cost_sek).label}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Snittkostnad</p>
            <p className="text-xl font-semibold">
              {stats.average_cost_sek_per_kwh != null
                ? `${stats.average_cost_sek_per_kwh.toFixed(2)} kr/kWh`
                : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Besparing</p>
            <p className="text-xl font-semibold">
              {stats.savings_sek != null ? formatSekAmount(stats.savings_sek).label : "—"}
            </p>
            <p className="text-xs text-muted-foreground">Jämfört med: omedelbar nät-laddning</p>
          </div>
        </div>
      )}

      {stats && stats.total_energy_kwh > 0 && (
        <div>
          <h4 className="mb-2 font-medium">Energimix</h4>
          <EnergyMixBar sources={stats.energy_sources} total={stats.total_energy_kwh} />
        </div>
      )}

      {latest && (
        <div className="rounded-md bg-muted/40 p-3">
          <h4 className="font-medium">Senaste laddningen</h4>
          <p className="text-sm text-muted-foreground">{formatTimeRange(latest.started_at, latest.ended_at)}</p>
          <div className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
            <span>Laddat: {formatKwh(latest.total_energy_kwh)}</span>
            <span>Kostnad: {latest.actual_cost_sek != null ? formatSekAmount(latest.actual_cost_sek).label : "—"}</span>
            <span>
              Snitt:{" "}
              {latest.average_cost_sek_per_kwh != null
                ? `${latest.average_cost_sek_per_kwh.toFixed(2)} kr/kWh`
                : "—"}
            </span>
            <span>
              Förnybar andel:{" "}
              {latest.renewable_share_pct != null ? `${latest.renewable_share_pct.toFixed(1)} %` : "—"}
            </span>
            <span>
              Besparing:{" "}
              {latest.savings_sek != null ? formatSekAmount(latest.savings_sek).label : "—"}
            </span>
          </div>
        </div>
      )}

      {sessions.length > 0 && (
        <div>
          <h4 className="mb-2 font-medium">Historik</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-1 pr-2">Start</th>
                  <th className="py-1 pr-2">kWh</th>
                  <th className="py-1 pr-2">Kostnad</th>
                  <th className="py-1 pr-2">Besparing</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr
                    key={s.id}
                    className="cursor-pointer border-b hover:bg-muted/30"
                    onClick={() => void openSession(s.id)}
                  >
                    <td className="py-1 pr-2">{new Date(s.started_at).toLocaleString("sv-SE")}</td>
                    <td className="py-1 pr-2">{s.total_energy_kwh?.toFixed(1) ?? "—"}</td>
                    <td className="py-1 pr-2">{s.actual_cost_sek != null ? formatSekAmount(s.actual_cost_sek).label : "—"}</td>
                    <td className="py-1 pr-2">{s.savings_sek != null ? formatSekAmount(s.savings_sek).label : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selected && (
        <div className="rounded-md border p-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">Session #{selected.id}</h4>
            <button type="button" className="text-sm underline" onClick={() => setSelected(null)}>
              Stäng
            </button>
          </div>
          <p className="text-sm text-muted-foreground">{formatTimeRange(selected.started_at, selected.ended_at)}</p>
          <EnergyMixBar
            sources={selected.energy_sources}
            total={selected.total_energy_kwh ?? selected.energy_sources.solar_direct_kwh}
          />
          {selected.intervals.length > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">
              {selected.intervals.length} intervall · kvalitet {selected.energy_quality ?? "—"}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
