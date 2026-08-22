"use client";

import { useEffect, useState } from "react";
import { ForecastValues, YearForecastResponse, fetchYearForecast } from "@/lib/api";

interface YearForecastViewProps {
  siteSlug: string;
}

const CONFIDENCE_LABELS: Record<YearForecastResponse["confidence"], string> = {
  very_low: "Mycket osäker",
  low: "Osäker",
  medium: "Medelhög säkerhet",
  high: "Högre säkerhet",
};

function currency(value: number): string {
  return value.toLocaleString("sv-SE", {
    style: "currency",
    currency: "SEK",
    maximumFractionDigits: 0,
  });
}

function kwh(value: number): string {
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 0 })} kWh`;
}

function monthLabel(value: string): string {
  const [year, month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("sv-SE", { month: "long", year: "numeric" }).format(
    new Date(year, month - 1, 1),
  );
}

function ForecastCard({
  label,
  total,
  projected,
  negative = false,
}: {
  label: string;
  total: number;
  projected: number;
  negative?: boolean;
}) {
  return (
    <div className={negative ? "forecast-card forecast-card-cost" : "forecast-card"}>
      <dt>{label}</dt>
      <dd>{negative ? "−" : ""}{currency(total)}</dd>
      <span>varav prognos {negative ? "−" : ""}{currency(projected)}</span>
    </div>
  );
}

export function YearForecastView({ siteSlug }: YearForecastViewProps) {
  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear + 1, currentYear + 2];
  const [year, setYear] = useState(currentYear);
  const [result, setResult] = useState<YearForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchYearForecast(siteSlug, year)
      .then((response) => {
        if (!active) return;
        setResult(response);
        setError(null);
      })
      .catch((reason) => {
        if (!active) return;
        setResult(null);
        setError(reason instanceof Error ? reason.message : "Kunde inte skapa prognosen.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [siteSlug, year]);

  const total: ForecastValues | null = result?.total ?? null;
  const forecast: ForecastValues | null = result?.forecast ?? null;
  const ownEnergyKwh = total
    ? total.solar_self_consumed_kwh + total.battery_self_consumed_kwh
    : 0;
  const ownEnergySavingsSek = total
    ? total.solar_savings_sek + total.battery_savings_sek
    : 0;
  const ownEnergyPercent =
    result?.import_baseline_kwh && result.import_baseline_kwh > 0
      ? (ownEnergyKwh / result.import_baseline_kwh) * 100
      : 0;
  const netRange =
    result && total
      ? [
          total.net_sek * (1 - result.uncertainty_pct / 100),
          total.net_sek * (1 + result.uncertainty_pct / 100),
        ].sort((left, right) => left - right)
      : [0, 0];

  return (
    <section className="peaks-section forecast-section" aria-labelledby="forecast-title">
      <div className="peaks-header">
        <div>
          <h3 id="forecast-title" className="section-title">Helårsprognos</h3>
          <p className="muted peaks-intro">
            Samlad prognos för energi och ekonomi under valt år.
          </p>
        </div>
        <label className="peaks-year">
          <span>Prognosår</span>
          <select
            aria-label="Välj prognosår"
            value={year}
            onChange={(event) => setYear(Number(event.target.value))}
          >
            {years.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <p className="muted">Beräknar helårsprognos…</p>
      ) : error ? (
        <p className="form-error" role="alert">{error}</p>
      ) : result && total && forecast ? (
        <>
          <div className="forecast-status">
            <span className={`forecast-confidence forecast-confidence-${result.confidence}`}>
              {CONFIDENCE_LABELS[result.confidence]}
            </span>
            <span>±{result.uncertainty_pct}%</span>
            <span>{result.observed_days} dagar mätdata</span>
            {result.import_baseline_year && (
              <span>
                Köpt el: {result.import_baseline_year}
                {result.import_baseline_estimated ? " (uppskattad månadsfördelning)" : ""}
              </span>
            )}
          </div>

          {result.import_baseline_kwh && result.import_baseline_year && (
            <div
              className="forecast-own-energy"
              aria-label={`Egen el jämfört med ${result.import_baseline_year}`}
            >
              <div className="forecast-own-energy-heading">
                <div>
                  <span className="forecast-own-energy-label">
                    Egen el mot {result.import_baseline_year}
                  </span>
                  <strong>
                    {ownEnergyPercent.toLocaleString("sv-SE", { maximumFractionDigits: 1 })}%
                  </strong>
                </div>
                <p>
                  Solpaneler och batteri motsvarar {kwh(ownEnergyKwh)} av baslinjen på{" "}
                  {kwh(result.import_baseline_kwh)} köpt el.
                </p>
              </div>
              <div
                className="forecast-own-energy-track"
                role="progressbar"
                aria-label="Andel ersatt med egen el"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.min(100, Math.round(ownEnergyPercent * 10) / 10)}
              >
                <span style={{ width: `${Math.min(100, ownEnergyPercent)}%` }} />
              </div>
              <div className="forecast-own-energy-details">
                <span>Sol: {kwh(total.solar_self_consumed_kwh)}</span>
                <span>Batteri: {kwh(total.battery_self_consumed_kwh)}</span>
                <span>Sparat: {currency(ownEnergySavingsSek)}</span>
              </div>
            </div>
          )}

          <dl className="forecast-summary">
            <ForecastCard
              label="Sparat med sol"
              total={total.solar_savings_sek}
              projected={forecast.solar_savings_sek}
            />
            <ForecastCard
              label="Sparat med batteri"
              total={total.battery_savings_sek}
              projected={forecast.battery_savings_sek}
            />
            <ForecastCard
              label="Såld el"
              total={total.export_revenue_sek}
              projected={forecast.export_revenue_sek}
            />
            <ForecastCard
              label="Köpt el"
              total={total.grid_import_cost_sek}
              projected={forecast.grid_import_cost_sek}
              negative
            />
            <div className="forecast-card forecast-card-net">
              <dt>Prognostiserat netto</dt>
              <dd>{currency(total.net_sek)}</dd>
              <span>intervall cirka {currency(netRange[0])}–{currency(netRange[1])}</span>
            </div>
          </dl>

          <p className="muted forecast-method">
            Faktiska värden används där mätdata finns. Resterande dagar beräknas från anläggningens
            uppmätta nivåer, svensk säsongsvariation för sol och förbrukning samt priserna i
            konfigurationen.
            {result.import_baseline_source && (
              <> Köpt el kalibreras mot {result.import_baseline_source}.</>
            )} Långtidsväder ingår inte.
          </p>

          <div className="peaks-table-wrap">
            <table className="peaks-table forecast-table">
              <thead>
                <tr>
                  <th scope="col">Månad</th>
                  <th scope="col">Egen solel</th>
                  <th scope="col">Batteri</th>
                  <th scope="col">Såld el</th>
                  <th scope="col">Köpt el</th>
                  <th scope="col">Netto</th>
                </tr>
              </thead>
              <tbody>
                {result.months.map((month) => (
                  <tr key={month.month}>
                    <th scope="row">{monthLabel(month.month)}</th>
                    <td>{kwh(month.total.solar_self_consumed_kwh)}</td>
                    <td>{kwh(month.total.battery_self_consumed_kwh)}</td>
                    <td>{kwh(month.total.exported_kwh)}</td>
                    <td>{kwh(month.total.imported_kwh)}</td>
                    <td>{currency(month.total.net_sek)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
