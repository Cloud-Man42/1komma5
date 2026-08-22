"use client";

import { useEffect, useMemo, useState } from "react";
import {
  FinancialStat,
  FinancialStatsResponse,
  PeakPeriod,
  fetchFinancialStats,
} from "@/lib/api";
import { formatSekAmount } from "@/lib/prices";

interface FinancialStatsViewProps {
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

function formatKwh(value: number): string {
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`;
}

export function FinancialStatsView({ siteSlug }: FinancialStatsViewProps) {
  const [period, setPeriod] = useState<PeakPeriod>("day");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [annualResponse, setAnnualResponse] = useState<FinancialStatsResponse | null>(null);
  const [response, setResponse] = useState<FinancialStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [annualLoading, setAnnualLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [annualError, setAnnualError] = useState<string | null>(null);

  const availableYears = useMemo(
    () =>
      (annualResponse?.stats ?? [])
        .map((stat) => Number(stat.period_start))
        .filter(Number.isFinite)
        .sort((a, b) => b - a),
    [annualResponse],
  );

  useEffect(() => {
    let active = true;
    fetchFinancialStats(siteSlug, "year")
      .then((result) => {
        if (!active) return;
        setAnnualResponse(result);
        setAnnualError(null);
        const years = result.stats.map((stat) => Number(stat.period_start)).filter(Number.isFinite);
        if (years.length > 0) setSelectedYear(Math.max(...years));
      })
      .catch((reason) => {
        if (active) {
          setAnnualError(
            reason instanceof Error ? reason.message : "Kunde inte läsa ekonomisk statistik.",
          );
        }
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
      setResponse(annualResponse);
      setLoading(annualLoading);
      setError(annualError);
      return;
    }
    let active = true;
    setLoading(true);
    fetchFinancialStats(siteSlug, period, selectedYear)
      .then((result) => {
        if (!active) return;
        setResponse(result);
        setError(null);
      })
      .catch((reason) => {
        if (!active) return;
        setResponse(null);
        setError(
          reason instanceof Error ? reason.message : "Kunde inte läsa ekonomisk statistik.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [annualError, annualLoading, annualResponse, period, selectedYear, siteSlug]);

  const stats = response?.stats ?? [];
  const totals = useMemo(
    () =>
      stats.reduce(
        (sum, stat) => ({
          solar: sum.solar + stat.solar_savings_sek,
          battery: sum.battery + stat.battery_savings_sek,
          export: sum.export + stat.export_revenue_sek,
          import: sum.import + stat.grid_import_cost_sek,
        }),
        { solar: 0, battery: 0, export: 0, import: 0 },
      ),
    [stats],
  );
  const valuedEnergy = stats.reduce(
    (sum, stat) =>
      sum +
      stat.solar_self_consumed_kwh +
      stat.battery_self_consumed_kwh +
      stat.imported_kwh,
    0,
  );
  const pricedFraction =
    valuedEnergy > 0
      ? stats.reduce(
          (sum, stat) =>
            sum +
            stat.market_priced_fraction *
              (stat.solar_self_consumed_kwh +
                stat.battery_self_consumed_kwh +
                stat.imported_kwh),
          0,
        ) / valuedEnergy
      : 0;

  return (
    <section className="peaks-section finance-section" aria-labelledby="finance-title">
      <div className="peaks-header">
        <div>
          <h3 id="finance-title" className="section-title">Ekonomisk nytta</h3>
          <p className="muted peaks-intro">
            Beräknad besparing från egen el och batteri samt intäkt från såld el.
          </p>
        </div>
        {period !== "year" && (
          <label className="peaks-year">
            <span>År</span>
            <select
              aria-label="Välj statistikår"
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

      <div className="peaks-tabs" role="tablist" aria-label="Ekonomisk tidsperiod">
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

      {!loading && !error && stats.length > 0 && (
        <>
          <dl className="peaks-summary finance-summary">
            <div><dt>Sparat med sol</dt><dd>{formatSekAmount(totals.solar).label}</dd></div>
            <div><dt>Sparat med batteri</dt><dd>{formatSekAmount(totals.battery).label}</dd></div>
            <div><dt>Såld el</dt><dd>{formatSekAmount(totals.export).label}</dd></div>
            <div className="finance-cost">
              <dt>Kostnad köpt el</dt><dd>−{formatSekAmount(totals.import).label}</dd>
            </div>
            <div className="finance-total">
              <dt>Total ekonomisk nytta</dt>
              <dd>{formatSekAmount(totals.solar + totals.battery + totals.export).label}</dd>
            </div>
            <div className="finance-net">
              <dt>Netto efter köpt el</dt>
              <dd>
                {(totals.solar + totals.battery + totals.export - totals.import).toLocaleString(
                  "sv-SE",
                  { style: "currency", currency: "SEK" },
                )}
              </dd>
            </div>
          </dl>
          <p className="muted finance-method">
            Heartbeat-timpris används för {(pricedFraction * 100).toFixed(0)}% av den värderade
            egenanvändningen. Övrigt använder reservpriset{" "}
            {response?.fallback_purchase_price_sek_kwh.toFixed(2)} kr/kWh. Såld el värderas till{" "}
            {response?.export_compensation_sek_kwh.toFixed(2)} kr/kWh.
          </p>
        </>
      )}

      {loading ? (
        <p className="muted">Beräknar ekonomisk statistik…</p>
      ) : error ? (
        <p className="form-error" role="alert">{error}</p>
      ) : stats.length === 0 ? (
        <p className="muted">Det finns inte tillräckligt med mätdata för perioden.</p>
      ) : (
        <div className="peaks-table-wrap">
          <table className="peaks-table finance-table">
            <thead>
              <tr>
                <th scope="col">{period === "day" ? "Datum" : period === "month" ? "Månad" : "År"}</th>
                <th scope="col">Solel använd</th>
                <th scope="col">Sparat sol</th>
                <th scope="col">Batteri använt</th>
                <th scope="col">Sparat batteri</th>
                <th scope="col">Såld el</th>
                <th scope="col">Försäljning</th>
                <th scope="col">Köpt el</th>
                <th scope="col">Inköpskostnad</th>
              </tr>
            </thead>
            <tbody>
              {[...stats].reverse().map((stat: FinancialStat) => (
                <tr key={stat.period_start}>
                  <th scope="row">{formatPeriod(stat.period_start, period)}</th>
                  <td>{formatKwh(stat.solar_self_consumed_kwh)}</td>
                  <td>{formatSekAmount(stat.solar_savings_sek).label}</td>
                  <td>{formatKwh(stat.battery_self_consumed_kwh)}</td>
                  <td>{formatSekAmount(stat.battery_savings_sek).label}</td>
                  <td>{formatKwh(stat.exported_kwh)}</td>
                  <td>{formatSekAmount(stat.export_revenue_sek).label}</td>
                  <td>{formatKwh(stat.imported_kwh)}</td>
                  <td>−{formatSekAmount(stat.grid_import_cost_sek).label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
