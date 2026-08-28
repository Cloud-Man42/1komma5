"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SolarWeather } from "@/lib/api";
import { WeatherIcon } from "./weatherIcons";

function formatHour(iso: string, timezone?: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

function num(value: number | null | undefined, unit: string, digits = 0): string {
  if (value == null) return "—";
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: digits })} ${unit}`;
}

export function WeatherSolarPanel({
  weather,
  timezone,
  error,
}: {
  weather: SolarWeather | null;
  timezone?: string;
  error?: string | null;
}) {
  if (error) {
    return (
      <section className="idash-panel idash-weather-panel">
        <h2 className="idash-panel-title">VÄDER &amp; SOLPROGNOS</h2>
        <p className="idash-muted">{error}</p>
      </section>
    );
  }

  if (!weather) {
    return (
      <section className="idash-panel idash-weather-panel">
        <h2 className="idash-panel-title">VÄDER &amp; SOLPROGNOS</h2>
        <p className="idash-muted">Hämtar väderdata…</p>
      </section>
    );
  }

  const current = weather.current;
  const chartData = weather.hours.map((hour) => ({
    time: formatHour(hour.timestamp, timezone),
    irradiance: hour.ghi_wm2 ?? 0,
    production: hour.forecast_power_w != null ? Math.round(hour.forecast_power_w) : null,
    cloud: hour.cloud_cover_pct ?? 0,
  }));

  return (
    <section className="idash-panel idash-weather-panel">
      <h2 className="idash-panel-title">VÄDER &amp; SOLPROGNOS</h2>

      <div className="idash-weather-head">
        <div className="idash-weather-now">
          <WeatherIcon icon={current?.condition_icon} size={38} />
          <div>
            <p className="idash-weather-temp-main">
              {num(current?.temperature_c, "°C", 1)}
            </p>
            <p className="idash-weather-condition">{current?.condition_sv ?? "Okänt"}</p>
          </div>
        </div>
        <dl className="idash-weather-stats">
          <div>
            <dt>Vind</dt>
            <dd>{num(current?.wind_speed_ms, "m/s", 1)}</dd>
          </div>
          <div>
            <dt>Luftfuktighet</dt>
            <dd>{num(current?.relative_humidity_pct, "%")}</dd>
          </div>
          <div>
            <dt>Molntäcke</dt>
            <dd>{num(current?.cloud_cover_pct, "%")}</dd>
          </div>
          <div>
            <dt>Instrålning</dt>
            <dd>{num(current?.ghi_wm2, "W/m²")}</dd>
          </div>
        </dl>
      </div>

      {weather.solar_impact_sv ? (
        <p className="idash-weather-impact">{weather.solar_impact_sv}</p>
      ) : null}

      <div className="idash-weather-sun">
        <span>Soluppgång {weather.sunrise ? formatHour(weather.sunrise, timezone) : "—"}</span>
        <span>Solnedgång {weather.sunset ? formatHour(weather.sunset, timezone) : "—"}</span>
      </div>

      <div className="idash-weather-chart">
        {chartData.length === 0 ? (
          <p className="idash-muted">Ingen timprognos tillgänglig</p>
        ) : (
          <ResponsiveContainer width="100%" height={130}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.08)" vertical={false} />
              <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} interval={5} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} width={34} />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #334155", borderRadius: 8 }}
                labelStyle={{ color: "#e2e8f0" }}
                formatter={(value, name) => {
                  if (typeof value !== "number") return ["—", name];
                  const unit = name === "Instrålning" ? "W/m²" : "W";
                  return [`${Math.round(value)} ${unit}`, name];
                }}
              />
              <Area
                type="monotone"
                dataKey="irradiance"
                name="Instrålning"
                stroke="#fbbf24"
                fill="url(#idashIrradianceFill)"
                strokeWidth={2}
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="production"
                name="Produktion"
                stroke="#38bdf8"
                fill="url(#idashProductionFill)"
                strokeWidth={2}
                dot={false}
                connectNulls
              />
              <defs>
                <linearGradient id="idashIrradianceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#fbbf24" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="idashProductionFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.02} />
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <ul className="idash-weather-hours" aria-label="Timprognos">
        {weather.hours.slice(0, 8).map((hour) => (
          <li key={hour.timestamp}>
            <span className="idash-weather-hour-time">{formatHour(hour.timestamp, timezone)}</span>
            <WeatherIcon icon={hour.condition_icon} size={20} />
            <span className="idash-weather-hour-temp">{num(hour.temperature_c, "°", 0)}</span>
          </li>
        ))}
      </ul>

      <p className="idash-weather-source">
        Källa {weather.provider}
        {weather.source === "cache" ? ` · cache ${Math.round(weather.cache_age_minutes)} min` : ""}
        {weather.source === "fallback" ? " · reservdata" : ""}
      </p>
    </section>
  );
}
