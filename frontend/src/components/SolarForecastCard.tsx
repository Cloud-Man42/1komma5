"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SolarForecast, fetchSolarConfig, fetchSolarForecast, formatWatts } from "@/lib/api";

interface SolarForecastCardProps {
  siteSlug: string;
}

function kwh(value: number): string {
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`;
}

function pctCorrection(raw: number, corrected: number): string {
  if (raw <= 0) return "—";
  const pct = ((corrected - raw) / raw) * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)} %`;
}

export function SolarForecastCard({ siteSlug }: SolarForecastCardProps) {
  const [forecast, setForecast] = useState<SolarForecast | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const config = await fetchSolarConfig(siteSlug);
        if (!active) return;

        if (!config.complete) {
          setNeedsSetup(true);
          setForecast(null);
          setError(null);
          return;
        }

        setNeedsSetup(false);
        const data = await fetchSolarForecast(siteSlug);
        if (!active) return;
        setForecast(data);
        setError(null);
      } catch (e) {
        if (!active) return;
        setForecast(null);
        setError(e instanceof Error ? e.message : "Ingen solprognos");
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [siteSlug]);

  if (needsSetup) {
    return (
      <section className="forecast-section">
        <h3 className="section-title">Solprognos</h3>
        <p className="muted">
          Solprognos är inte konfigurerad för denna anläggning. Ange koordinater, kWp och aktivera
          prognosen under Inställningar.
        </p>
        <p>
          <Link href={`/config#solar-${siteSlug}`} className="back-link">
            Gå till solprofil →
          </Link>
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="forecast-section">
        <h3 className="section-title">Solprognos</h3>
        <p className="muted">{error}</p>
        <p>
          <Link href={`/config#solar-${siteSlug}`} className="back-link">
            Kontrollera solprofil →
          </Link>
        </p>
      </section>
    );
  }

  if (!forecast) return <p className="muted">Laddar solprognos…</p>;

  const peakTime = forecast.peak_time
    ? new Date(forecast.peak_time).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" })
    : "—";

  const rawTomorrow = forecast.raw_forecast_tomorrow_kwh ?? forecast.expected_tomorrow_kwh;
  const correctedTomorrow =
    forecast.corrected_forecast_tomorrow_kwh ?? forecast.expected_tomorrow_kwh;
  const learning =
    forecast.model_state === "NO_DATA" ||
    forecast.model_state === "LEARNING" ||
    (forecast.historical_samples ?? 0) === 0;
  const productionDays = forecast.production_days_observed ?? 0;
  const evaluatedDays = forecast.historical_samples ?? 0;

  const qualityClass = forecast.quality.toLowerCase().replace(/_/g, "-");

  return (
    <section className="forecast-section">
      <h3 className="section-title">Solprognos</h3>

      {correctedTomorrow != null ? (
        <dl className="metrics">
          <div>
            <dt>Imorgon</dt>
            <dd>{kwh(correctedTomorrow)}</dd>
          </div>
          {rawTomorrow != null ? (
            <>
              <div>
                <dt>Grundprognos</dt>
                <dd>{kwh(rawTomorrow)}</dd>
              </div>
              <div>
                <dt>EMIC-korrigering</dt>
                <dd>{pctCorrection(rawTomorrow, correctedTomorrow)}</dd>
              </div>
            </>
          ) : null}
          {forecast.confidence_score != null ? (
            <div>
              <dt>Confidence</dt>
              <dd>
                {Math.round(forecast.confidence_score)} % {forecast.confidence_label ?? ""}
              </dd>
            </div>
          ) : (
            <div>
              <dt>Confidence</dt>
              <dd>{Math.round(forecast.confidence * 100)} %</dd>
            </div>
          )}
        </dl>
      ) : null}

      {learning ? (
        <p className="muted">
          Modellen lär sig — träffsäkerhet byggs upp när EMIC utvärderat fler hela
          produktionsdagar mot prognos (
          {evaluatedDays} utvärderade
          {productionDays > evaluatedDays ? ` av ${productionDays} med mätdata` : ""} hittills).
        </p>
      ) : null}

      <h4 className="section-subtitle">Idag</h4>
      <dl className="metrics">
        <div>
          <dt>Hittills idag</dt>
          <dd>
            {kwh(forecast.actual_today_kwh)} faktiskt · {kwh(forecast.forecast_so_far_kwh)} prognos
          </dd>
        </div>
        <div>
          <dt>Förväntad produktion</dt>
          <dd>{kwh(forecast.expected_today_kwh)}</dd>
        </div>
        <div>
          <dt>Återstår idag</dt>
          <dd>{kwh(forecast.remaining_vs_expected_kwh)}</dd>
        </div>
        <div>
          <dt>Troligt intervall</dt>
          <dd>
            {kwh(forecast.lower_today_kwh)} – {kwh(forecast.upper_today_kwh)}
          </dd>
        </div>
        <div>
          <dt>Peak</dt>
          <dd>
            {formatWatts(forecast.peak_power_w)} kl {peakTime}
          </dd>
        </div>
      </dl>
      <p className={`forecast-status forecast-confidence-${qualityClass}`}>
        {forecast.quality} · {forecast.weather_summary}
      </p>
    </section>
  );
}
