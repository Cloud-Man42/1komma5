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

function pctVsForecast(actual: number, forecast: number): string {
  if (forecast <= 0) return "—";
  const pct = ((actual - forecast) / forecast) * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)} % mot prognos`;
}

export function SolarForecastCard({ siteSlug }: SolarForecastCardProps) {
  const [forecast, setForecast] = useState<SolarForecast | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

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

  const confScore = forecast.confidence_score ?? Math.round(forecast.confidence * 100);
  const confLabel = forecast.confidence_label ?? (confScore >= 75 ? "Hög" : confScore >= 45 ? "Medium" : "Låg");

  return (
    <section className="forecast-section solar-forecast-compact">
      <h3 className="section-title">Solprognos idag</h3>

      <p className="solar-forecast-hero">{kwh(forecast.expected_today_kwh)}</p>
      <p className="muted">
        Förväntat intervall {kwh(forecast.lower_today_kwh)} – {kwh(forecast.upper_today_kwh)}
      </p>
      <p className="muted">
        Confidence {confLabel} · {confScore} %
      </p>
      <p>
        Producerat hittills {kwh(forecast.actual_today_kwh)}
      </p>
      <p>
        Prognos vid denna tid {kwh(forecast.forecast_so_far_kwh)}
      </p>
      <p className="muted">{pctVsForecast(forecast.actual_today_kwh, forecast.forecast_so_far_kwh)}</p>

      <button type="button" className="link-button" onClick={() => setExpanded((v) => !v)}>
        {expanded ? "Dölj detaljer ▲" : "Visa detaljer ▼"}
      </button>

      {expanded ? (
        <>
          <h4 className="section-subtitle">Detaljer</h4>
          <dl className="metrics">
            <div>
              <dt>Återstår idag</dt>
              <dd>{kwh(forecast.remaining_vs_expected_kwh)}</dd>
            </div>
            <div>
              <dt>Peak</dt>
              <dd>
                {formatWatts(forecast.peak_power_w)} kl {peakTime}
              </dd>
            </div>
            {forecast.expected_tomorrow_kwh != null ? (
              <div>
                <dt>Imorgon</dt>
                <dd>{kwh(forecast.expected_tomorrow_kwh)}</dd>
              </div>
            ) : null}
          </dl>
          <p>
            <Link href={`/sites/${siteSlug}/solar/intelligence`} className="back-link">
              Solar Intelligence →
            </Link>
          </p>
        </>
      ) : null}
    </section>
  );
}
