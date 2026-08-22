"use client";

import { useEffect, useState } from "react";
import { SolarDiagnostics, fetchSolarDiagnostics } from "@/lib/api";

interface SolarDiagnosticsPanelProps {
  siteSlug: string;
}

const SOLAR_DEBUG =
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_SOLAR_DEBUG === "true";

export function SolarDiagnosticsPanel({ siteSlug }: SolarDiagnosticsPanelProps) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<SolarDiagnostics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!SOLAR_DEBUG || !open) return;
    let active = true;
    fetchSolarDiagnostics(siteSlug)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((e) => {
        if (active) {
          setData(null);
          setError(e instanceof Error ? e.message : "Kunde inte ladda diagnostik");
        }
      });
    return () => {
      active = false;
    };
  }, [siteSlug, open]);

  if (!SOLAR_DEBUG) return null;

  return (
    <section className="peaks-section">
      <button type="button" className="back-link" onClick={() => setOpen((v) => !v)}>
        {open ? "Dölj" : "Visa"} solprognos-diagnostik (debug)
      </button>
      {open ? (
        error ? (
          <p className="muted">{error}</p>
        ) : !data ? (
          <p className="muted">Laddar diagnostik…</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Datum</th>
                  <th>Raw</th>
                  <th>Korrigerad</th>
                  <th>Faktisk</th>
                  <th>Fel</th>
                  <th>Raw fel</th>
                  <th>Väder</th>
                  <th>CF</th>
                  <th>Träning</th>
                </tr>
              </thead>
              <tbody>
                {data.observations.map((o) => (
                  <tr key={o.forecast_date}>
                    <td>{o.forecast_date}</td>
                    <td>{o.forecast_kwh_raw?.toFixed(1) ?? "—"}</td>
                    <td>{o.forecast_kwh_corrected?.toFixed(1) ?? "—"}</td>
                    <td>{o.actual_kwh?.toFixed(1) ?? "—"}</td>
                    <td>{o.absolute_error_kwh?.toFixed(2) ?? "—"}</td>
                    <td>{o.raw_absolute_error_kwh?.toFixed(2) ?? "—"}</td>
                    <td>{o.weather_condition_bucket ?? "—"}</td>
                    <td>{o.correction_factor_used?.toFixed(3) ?? "—"}</td>
                    <td>
                      {o.training_eligible ? "Ja" : o.exclusion_reason ?? "Nej"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : null}
    </section>
  );
}
