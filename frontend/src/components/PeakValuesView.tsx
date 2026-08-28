"use client";

import { useEffect, useMemo, useState } from "react";
import {
  PeakPeriod,
  PeakReading,
  fetchSitePeaks,
  formatWatts,
} from "@/lib/api";

interface PeakValuesViewProps {
  siteSlug: string;
}

const PERIOD_LABELS: Record<PeakPeriod, string> = {
  day: "Dagar",
  month: "Månader",
  year: "År",
};

function formatPeriod(value: string, period: PeakPeriod): string {
  if (period === "year") return value;
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("sv-SE", {
    year: "numeric",
    month: period === "month" ? "long" : "short",
    ...(period === "day" ? { day: "numeric" } : {}),
  }).format(new Date(year, month - 1, day ?? 1));
}

export function PeakValuesView({ siteSlug }: PeakValuesViewProps) {
  const [period, setPeriod] = useState<PeakPeriod>("day");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [annualPeaks, setAnnualPeaks] = useState<PeakReading[]>([]);
  const [annualLoading, setAnnualLoading] = useState(true);
  const [annualError, setAnnualError] = useState<string | null>(null);
  const [peaks, setPeaks] = useState<PeakReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchSitePeaks(siteSlug, "year")
      .then((response) => {
        if (!active) return;
        const years = response.peaks
          .map((peak) => Number(peak.period_start))
          .filter(Number.isFinite)
          .sort((a, b) => b - a);
        setAnnualPeaks(response.peaks);
        setAvailableYears(years);
        setAnnualError(null);
        if (years.length > 0) setSelectedYear(years[0]);
      })
      .catch((reason) => {
        if (!active) return;
        setAvailableYears([]);
        setAnnualError(
          reason instanceof Error ? reason.message : "Kunde inte läsa årliga peakvärden.",
        );
      })
      .finally(() => {
        if (active) setAnnualLoading(false);
      });
    return () => {
      active = false;
    };
  }, [siteSlug]);

  useEffect(() => {
    if (period === "year") {
      setPeaks(annualPeaks);
      setLoading(annualLoading);
      setError(annualError);
      return;
    }

    let active = true;
    setLoading(true);
    fetchSitePeaks(siteSlug, period, selectedYear)
      .then((response) => {
        if (!active) return;
        setPeaks(response.peaks);
        setError(null);
      })
      .catch((reason) => {
        if (!active) return;
        setPeaks([]);
        setError(reason instanceof Error ? reason.message : "Kunde inte läsa peakvärden.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [annualError, annualLoading, annualPeaks, period, selectedYear, siteSlug]);

  const highest = useMemo(
    () => ({
      solar: Math.max(0, ...peaks.map((peak) => peak.solar_production_w)),
      consumption: Math.max(0, ...peaks.map((peak) => peak.consumption_w ?? 0)),
      charge: Math.max(0, ...peaks.map((peak) => peak.battery_charge_w)),
      discharge: Math.max(0, ...peaks.map((peak) => peak.battery_discharge_w)),
    }),
    [peaks],
  );

  return (
    <section className="peaks-section" aria-labelledby="peaks-title">
      <div className="peaks-header">
        <div>
          <h3 id="peaks-title" className="section-title">Peakvärden</h3>
          <p className="muted peaks-intro">
            Högsta uppmätta effekt för solproduktion, husförbrukning, batteriladdning och batteriurladdning.
          </p>
        </div>
        {period !== "year" && (
          <label className="peaks-year">
            <span>År</span>
            <select
              aria-label="Välj år"
              value={selectedYear}
              onChange={(event) => setSelectedYear(Number(event.target.value))}
            >
              {(availableYears.length > 0 ? availableYears : [selectedYear]).map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="peaks-tabs" role="tablist" aria-label="Tidsperiod">
        {(Object.keys(PERIOD_LABELS) as PeakPeriod[]).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={period === value}
            className={period === value ? "peaks-tab peaks-tab-active" : "peaks-tab"}
            onClick={() => setPeriod(value)}
          >
            {PERIOD_LABELS[value]}
          </button>
        ))}
      </div>

      {!loading && !error && peaks.length > 0 && (
        <dl className="peaks-summary">
          <div><dt>Högsta solpeak</dt><dd>{formatWatts(highest.solar)}</dd></div>
          <div><dt>Högsta förbrukning</dt><dd>{formatWatts(highest.consumption)}</dd></div>
          <div><dt>Högsta laddning</dt><dd>{formatWatts(highest.charge)}</dd></div>
          <div><dt>Högsta urladdning</dt><dd>{formatWatts(highest.discharge)}</dd></div>
        </dl>
      )}

      {loading ? (
        <p className="muted">Läser peakvärden…</p>
      ) : error ? (
        <p className="form-error" role="alert">{error}</p>
      ) : peaks.length === 0 ? (
        <p className="muted">Det finns inga peakvärden för den valda perioden.</p>
      ) : (
        <div className="peaks-table-wrap">
          <table className="peaks-table">
            <thead>
              <tr>
                <th scope="col">{period === "day" ? "Datum" : period === "month" ? "Månad" : "År"}</th>
                <th scope="col">Solproduktion</th>
                <th scope="col">Husförbrukning</th>
                <th scope="col">Batteriladdning</th>
                <th scope="col">Batteriurladdning</th>
              </tr>
            </thead>
            <tbody>
              {[...peaks].reverse().map((peak) => (
                <tr key={peak.period_start}>
                  <th scope="row">{formatPeriod(peak.period_start, period)}</th>
                  <td>{formatWatts(peak.solar_production_w)}</td>
                  <td>{formatWatts(peak.consumption_w ?? 0)}</td>
                  <td>{formatWatts(peak.battery_charge_w)}</td>
                  <td>{formatWatts(peak.battery_discharge_w)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
