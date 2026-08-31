"use client";



import type { CSSProperties, ReactNode } from "react";

import {

  Area,

  AreaChart,

  Bar,

  BarChart,

  CartesianGrid,

  Cell,

  ComposedChart,

  Legend,

  Line,

  Pie,

  PieChart,

  ReferenceLine,

  ResponsiveContainer,

  Tooltip,

  XAxis,

  YAxis,

} from "recharts";

import { CircularGauge } from "@/components/intelligence-dashboard/CircularGauge";

import { Sparkline } from "@/components/intelligence-dashboard/Sparkline";

import {

  confidenceHeadlineSv,

  confidenceTierSv,

  modelStateSv,

} from "@/components/intelligence-dashboard/confidenceLabels";

import type { SolarAccuracy, SolarForecast, SolarWeather } from "@/lib/api";

import {

  chartYMax,

  formatSolarKwh,

  formatSolarKw,

  type SolarChartResolution,

  type SolarComparisonBar,

  type SolarDayStats,

  type SolarKpiMetrics,

  type SolarKpiSparklines,

  type SolarMultiDayRow,

  type SolarPeriodSlice,

  type SolarProductionChartPoint,

  type SolarWeatherFactors,

} from "./solarDashboardHelpers";



function KpiCard({

  title,

  value,

  subtext,

  detail,

  accent,

  sparkValues,

  gauge,

}: {

  title: string;

  value: string;

  subtext: string;

  detail?: string;

  accent: string;

  sparkValues?: number[];

  gauge?: ReactNode;

}) {

  return (

    <article className="sdash-kpi-card" style={{ "--sdash-accent": accent } as CSSProperties}>

      {sparkValues && sparkValues.length > 1 ? (

        <div className="sdash-kpi-spark-bg" aria-hidden="true">

          <Sparkline values={sparkValues} color={accent} className="sdash-kpi-spark" />

        </div>

      ) : null}

      <p className="sdash-kpi-label">{title}</p>

      {gauge ?? <strong className="sdash-kpi-value">{value}</strong>}

      <p className="sdash-kpi-sub">{subtext}</p>

      {detail ? <p className="sdash-kpi-detail">{detail}</p> : null}

    </article>

  );

}



export function SolarKpiStrip({

  kpi,

  sparklines,

}: {

  kpi: SolarKpiMetrics;

  sparklines: SolarKpiSparklines;

}) {

  const confLabel = confidenceTierSv(kpi.confidencePct);

  return (

    <div className="sdash-kpi-strip" data-testid="solar-kpi-strip">

      <KpiCard

        title="PROGNOS IDAG"

        accent="#fb923c"

        value={formatSolarKwh(kpi.forecastTodayKwh)}

        subtext="Förväntad produktion"

        sparkValues={sparklines.forecast}

      />

      <KpiCard

        title="PRODUCERAT HITTILLS"

        accent="#38bdf8"

        value={formatSolarKwh(kpi.producedSoFarKwh)}

        subtext="Verklig produktion"

        sparkValues={sparklines.actual}

      />

      <KpiCard

        title="PROGNOS VID NU"

        accent="#fbbf24"

        value={formatSolarKwh(kpi.forecastAtNowKwh)}

        subtext="Förväntat hittills"

      />

      <KpiCard

        title="TILLIT"

        accent="#4ade80"

        value={kpi.confidencePct != null ? `${kpi.confidencePct}%` : "—"}

        subtext={confLabel}

        gauge={

          kpi.confidencePct != null ? (

            <CircularGauge

              value={kpi.confidencePct}

              label={`${kpi.confidencePct}%`}

              sublabel={confLabel}

              color="#4ade80"

              size={72}

            />

          ) : undefined

        }

      />

      <KpiCard

        title="FÖRVÄNTAT INTERVALL"

        accent="#c084fc"

        value={kpi.intervalLabel}

        subtext="Dagens spann"

      />

      <KpiCard

        title="NÄSTA TIMME"

        accent="#fb923c"

        value={kpi.nextHourForecastKw != null ? `${kpi.nextHourForecastKw.toFixed(1)} kW` : "—"}

        subtext="Prognos effekt"

      />

    </div>

  );

}



export function SolarProductionChartPanel({

  series,

  resolution,

  onResolutionChange,

  timezone,

}: {

  series: SolarProductionChartPoint[];

  resolution: SolarChartResolution;

  onResolutionChange: (value: SolarChartResolution) => void;

  timezone: string;

}) {

  const yMax = chartYMax(series);

  const nowLabel = new Date().toLocaleTimeString("sv-SE", {

    hour: "2-digit",

    minute: "2-digit",

    timeZone: timezone,

  });

  const hasBattery = series.some((p) => p.batterySocPct != null);

  const hasYesterday = series.some((p) => p.yesterdayKw != null && p.yesterdayKw > 0);



  return (

    <section className="sdash-panel sdash-production-panel" data-testid="solar-production-chart">

      <header className="sdash-panel-head">

        <h2 className="sdash-panel-title">PROGNOS VS VERKLIG PRODUKTION</h2>

        <label className="sdash-resolution">

          <select

            aria-label="Upplösning"

            value={resolution}

            onChange={(e) => onResolutionChange(Number(e.target.value) as SolarChartResolution)}

          >

            <option value={15}>15 min</option>

            <option value={60}>60 min</option>

          </select>

        </label>

      </header>

      {series.length === 0 ? (

        <p className="sdash-muted">Ingen produktionsdata ännu.</p>

      ) : (

        <div className="sdash-chart-wrap">

          <ResponsiveContainer width="100%" height={280}>

            <ComposedChart data={series} margin={{ top: 8, right: hasBattery ? 36 : 8, left: 0, bottom: 0 }}>

              <CartesianGrid stroke="rgba(148,163,184,0.1)" strokeDasharray="4 4" vertical={false} />

              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} interval="preserveStartEnd" />

              <YAxis

                yAxisId="power"

                tick={{ fill: "#64748b", fontSize: 10 }}

                domain={[0, yMax]}

                width={32}

                label={{ value: "kW", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 10 }}

              />

              {hasBattery ? (

                <YAxis

                  yAxisId="soc"

                  orientation="right"

                  tick={{ fill: "#4ade80", fontSize: 10 }}

                  domain={[0, 100]}

                  width={28}

                />

              ) : null}

              <Tooltip

                contentStyle={{ background: "#111827", border: "1px solid #334155", borderRadius: 8 }}

                labelStyle={{ color: "#e2e8f0" }}

                formatter={(value: number, name: string) => [

                  name === "Batteri %" ? `${Math.round(value)}%` : `${value.toLocaleString("sv-SE", { maximumFractionDigits: 2 })} kW`,

                  name,

                ]}

              />

              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />

              <Line

                yAxisId="power"

                type="monotone"

                dataKey="forecastKw"

                name="Prognos"

                stroke="#fb923c"

                strokeDasharray="6 4"

                strokeWidth={2.5}

                dot={false}

                connectNulls={false}

                isAnimationActive={false}

              />

              <Line

                yAxisId="power"

                type="monotone"

                dataKey="actualKw"

                name="Verklig"

                stroke="#38bdf8"

                strokeWidth={2.5}

                dot={false}

                connectNulls={false}

                isAnimationActive={false}

              />

              {hasYesterday ? (

                <Line

                  yAxisId="power"

                  type="monotone"

                  dataKey="yesterdayKw"

                  name="Igår"

                  stroke="#64748b"

                  strokeWidth={1.5}

                  dot={false}

                  connectNulls

                />

              ) : null}

              {hasBattery ? (

                <Line

                  yAxisId="soc"

                  type="monotone"

                  dataKey="batterySocPct"

                  name="Batteri %"

                  stroke="#4ade80"

                  strokeWidth={1.5}

                  dot={false}

                  connectNulls

                />

              ) : null}

              <ReferenceLine yAxisId="power" x={nowLabel} stroke="#94a3b8" strokeDasharray="4 4" label="Nu" />

            </ComposedChart>

          </ResponsiveContainer>

        </div>

      )}

    </section>

  );

}



export function SolarDayStatsPanel({ stats }: { stats: SolarDayStats }) {

  return (

    <section className="sdash-panel sdash-day-stats" data-testid="solar-day-stats">

      <h2 className="sdash-panel-title">DAGENS SOLDATA</h2>

      <dl className="sdash-stat-list">

        <div><dt>Soluppgång</dt><dd>{stats.sunrise ?? "—"}</dd></div>

        <div><dt>Solnedgång</dt><dd>{stats.sunset ?? "—"}</dd></div>

        <div><dt>Max prognos</dt><dd>{stats.maxForecastKw != null ? `${stats.maxForecastKw} kW` : "—"}</dd></div>

        <div><dt>Max verklig</dt><dd>{stats.maxActualKw != null ? `${stats.maxActualKw} kW` : "—"}</dd></div>

        <div><dt>Snitt prognos</dt><dd>{stats.avgForecastKw != null ? `${stats.avgForecastKw} kW` : "—"}</dd></div>

        <div><dt>Snitt verklig</dt><dd>{stats.avgActualKw != null ? `${stats.avgActualKw} kW` : "—"}</dd></div>

        <div><dt>Specifik avkastning</dt><dd>{stats.specificYieldWhPerWp != null ? `${stats.specificYieldWhPerWp} Wh/Wp` : "—"}</dd></div>

      </dl>

    </section>

  );

}



export function SolarMultiDayPanel({ rows }: { rows: SolarMultiDayRow[] }) {

  return (

    <section className="sdash-panel sdash-multiday-panel" data-testid="solar-multiday">

      <h2 className="sdash-panel-title">PROGNOS-ÖVERSIKT</h2>

      {rows.length === 0 ? (

        <p className="sdash-muted">Ingen flerdagarsprognos tillgänglig.</p>

      ) : (

        <ul className="sdash-multiday-list">

          {rows.map((row) => (

            <li key={row.dateKey}>

              <span>{row.label}{row.isPartial ? " (partiell)" : ""}</span>

              <strong>{row.expectedKwh != null ? formatSolarKwh(row.expectedKwh) : "—"}</strong>

            </li>

          ))}

        </ul>

      )}

    </section>

  );

}



export function SolarDistributionPanel({ slices }: { slices: SolarPeriodSlice[] }) {

  const total = slices.reduce((sum, s) => sum + s.kwh, 0);

  return (

    <section className="sdash-panel sdash-distribution-panel" data-testid="solar-distribution">

      <h2 className="sdash-panel-title">PROGNOSFÖRDELNING IDAG</h2>

      {total <= 0 ? (

        <p className="sdash-muted">Ingen fördelningsdata.</p>

      ) : (

        <div className="sdash-distribution-body">

          <ResponsiveContainer width="100%" height={160}>

            <PieChart>

              <Pie

                data={slices}

                dataKey="kwh"

                nameKey="label"

                innerRadius={42}

                outerRadius={64}

                paddingAngle={2}

              >

                {slices.map((slice) => (

                  <Cell key={slice.id} fill={slice.color} />

                ))}

              </Pie>

              <Tooltip formatter={(value: number) => formatSolarKwh(value)} />

            </PieChart>

          </ResponsiveContainer>

          <ul className="sdash-distribution-legend">

            {slices.map((slice) => (

              <li key={slice.id}>

                <span style={{ background: slice.color }} />

                <span>{slice.label}</span>

                <strong>{Math.round(slice.pct)}% · {formatSolarKwh(slice.kwh)}</strong>

              </li>

            ))}

          </ul>

        </div>

      )}

    </section>

  );

}



export function SolarComparisonPanel({ bars }: { bars: SolarComparisonBar[] }) {

  const chartData = bars.map((b) => ({

    label: b.label,

    prognosKwh: b.expectedKwh ?? 0,

    verkligKwh: b.actualKwh ?? 0,

    ratioPct: b.ratioPct,

  }));

  const yMax = Math.max(10, ...chartData.flatMap((row) => [row.prognosKwh, row.verkligKwh]));



  return (

    <section className="sdash-panel sdash-comparison-panel" data-testid="solar-comparison">

      <h2 className="sdash-panel-title">PROGNOSJÄMFÖRELSE</h2>

      <p className="sdash-muted sdash-comparison-note">Jämför korrigerad dagsprognos med uppmätt produktion.</p>

      {chartData.length === 0 ? (

        <p className="sdash-muted">Ingen prestandahistorik ännu.</p>

      ) : (

        <div className="sdash-chart-wrap">

          <ResponsiveContainer width="100%" height={180}>

            <BarChart data={chartData} barGap={6} barCategoryGap="24%">

              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />

              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} />

              <YAxis

                tick={{ fill: "#94a3b8", fontSize: 10 }}

                width={28}

                domain={[0, Math.ceil(yMax * 1.15)]}

                allowDataOverflow

              />

              <Tooltip

                formatter={(value: number, name: string) => [formatSolarKwh(value), name]}

                contentStyle={{ background: "#111827", border: "1px solid #334155", borderRadius: 8 }}

              />

              <Legend wrapperStyle={{ fontSize: 11 }} />

              <Bar dataKey="prognosKwh" fill="#fb923c" name="Prognos" radius={[4, 4, 0, 0]} />

              <Bar dataKey="verkligKwh" fill="#38bdf8" name="Verklig" radius={[4, 4, 0, 0]} />

            </BarChart>

          </ResponsiveContainer>

        </div>

      )}

    </section>

  );

}



export function SolarWeatherFactorsPanel({ factors }: { factors: SolarWeatherFactors }) {

  return (

    <section className="sdash-panel sdash-weather-factors" data-testid="solar-weather-factors">

      <h2 className="sdash-panel-title">PROGNOSFAKTORER</h2>

      <dl className="sdash-stat-list sdash-stat-grid">

        <div><dt>Max GHI</dt><dd>{factors.maxGhi != null ? `${factors.maxGhi} W/m²` : "—"}</dd></div>

        <div><dt>Snitt GHI</dt><dd>{factors.avgGhi != null ? `${factors.avgGhi} W/m²` : "—"}</dd></div>

        <div><dt>Max temp</dt><dd>{factors.maxTempC != null ? `${factors.maxTempC}°C` : "—"}</dd></div>

        <div><dt>Snitt temp</dt><dd>{factors.avgTempC != null ? `${factors.avgTempC}°C` : "—"}</dd></div>

        <div><dt>Max vind</dt><dd>{factors.maxWindMs != null ? `${factors.maxWindMs} m/s` : "—"}</dd></div>

        <div><dt>Snitt vind</dt><dd>{factors.avgWindMs != null ? `${factors.avgWindMs} m/s` : "—"}</dd></div>

        <div><dt>Molnighet</dt><dd>{factors.avgCloudPct != null ? `${factors.avgCloudPct}%` : "—"}</dd></div>

        <div><dt>Nederbörd</dt><dd>{factors.totalPrecipMm != null ? `${factors.totalPrecipMm} mm` : "—"}</dd></div>

      </dl>

    </section>

  );

}



export function SolarTomorrowPanel({

  points,

  expectedKwh,

  message,

  stale = false,

}: {

  points: { label: string; forecastKw: number; energyKwh: number }[];

  expectedKwh: number | null;

  message?: string | null;

  stale?: boolean;

}) {

  return (

    <section className="sdash-panel sdash-tomorrow-panel" data-testid="solar-tomorrow">

      <h2 className="sdash-panel-title">PROGNOS IMORGON</h2>

      {expectedKwh != null ? (

        <p className="sdash-tomorrow-total">

          Förväntat totalt: <strong>{formatSolarKwh(expectedKwh)}</strong>

        </p>

      ) : null}

      {message ? (

        <p className={stale ? "sdash-warn" : "sdash-muted"} role={stale ? "alert" : undefined}>

          {message}

        </p>

      ) : null}

      {points.length > 0 ? (

        <div className="sdash-chart-wrap">

          <ResponsiveContainer width="100%" height={220}>

            <AreaChart data={points}>

              <defs>

                <linearGradient id="sdashTomorrowFill" x1="0" y1="0" x2="0" y2="1">

                  <stop offset="0%" stopColor="#fb923c" stopOpacity={0.4} />

                  <stop offset="100%" stopColor="#fb923c" stopOpacity={0.02} />

                </linearGradient>

              </defs>

              <CartesianGrid stroke="rgba(148,163,184,0.1)" vertical={false} />

              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} interval={3} />

              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} width={28} />

              <Tooltip formatter={(value: number) => `${value.toFixed(2)} kW`} />

              <Area type="monotone" dataKey="forecastKw" stroke="#fb923c" fill="url(#sdashTomorrowFill)" name="Prognos" />

            </AreaChart>

          </ResponsiveContainer>

        </div>

      ) : expectedKwh == null && !message ? (

        <p className="sdash-muted">Ingen imorgon-prognos tillgänglig ännu.</p>

      ) : null}

    </section>

  );

}



export function SolarWeatherPanel({ weather }: { weather: SolarWeather | null }) {

  if (!weather) {

    return (

      <section className="sdash-panel">

        <h2 className="sdash-panel-title">VÄDER</h2>

        <p className="sdash-muted">Ingen väderdata tillgänglig.</p>

      </section>

    );

  }

  return (

    <section className="sdash-panel sdash-weather-panel" data-testid="solar-weather">

      <h2 className="sdash-panel-title">VÄDER &amp; SOLPÅVERKAN</h2>

      <p className="sdash-weather-impact">{weather.solar_impact_sv}</p>

      <p className="sdash-muted">Källa: {weather.provider} · {weather.source}</p>

      {weather.current ? (

        <dl className="sdash-stat-list">

          <div><dt>Nu</dt><dd>{weather.current.condition_sv}</dd></div>

          <div><dt>Temperatur</dt><dd>{weather.current.temperature_c != null ? `${weather.current.temperature_c}°C` : "—"}</dd></div>

          <div><dt>Moln</dt><dd>{weather.current.cloud_cover_pct != null ? `${weather.current.cloud_cover_pct}%` : "—"}</dd></div>

        </dl>

      ) : null}

    </section>

  );

}



export function SolarAccuracyPanel({

  accuracy,

  forecast,

}: {

  accuracy: SolarAccuracy | null;

  forecast: SolarForecast | null;

}) {

  if (!accuracy) {

    return (

      <section className="sdash-panel" data-testid="solar-accuracy">

        <h2 className="sdash-panel-title">MODELLKVALITET</h2>

        <p className="sdash-muted">Ingen modellkvalitetsdata tillgänglig.</p>

      </section>

    );

  }



  const confPct =
    accuracy.confidence_score != null ? Math.round(accuracy.confidence_score) : null;



  return (

    <section className="sdash-panel sdash-accuracy-panel" data-testid="solar-accuracy">

      <h2 className="sdash-panel-title">MODELLKVALITET</h2>

      <div className="sdash-accuracy-head">

        <CircularGauge

          value={confPct ?? 0}

          label={confPct != null ? `${confPct}%` : "—"}

          sublabel={accuracy.confidence_label ?? confidenceHeadlineSv(confPct)}

          color="#4ade80"

          size={100}

        />

        <dl className="sdash-stat-list">

          <div><dt>Modellstatus</dt><dd>{modelStateSv(accuracy.model_state) ?? accuracy.model_state}</dd></div>

          <div><dt>MAPE 7d</dt><dd>{accuracy.mape_7d_pct != null ? `${accuracy.mape_7d_pct.toFixed(1)}%` : "—"}</dd></div>

          <div><dt>MAPE 30d</dt><dd>{accuracy.mape_30d_pct != null ? `${accuracy.mape_30d_pct.toFixed(1)}%` : "—"}</dd></div>

          <div><dt>MAE 30d</dt><dd>{accuracy.mae_kwh_30d != null ? formatSolarKwh(accuracy.mae_kwh_30d) : "—"}</dd></div>

          <div><dt>Bias 30d</dt><dd>{accuracy.bias_pct_30d != null ? `${accuracy.bias_pct_30d.toFixed(1)}%` : "—"}</dd></div>

          <div><dt>Träningsdagar</dt><dd>{accuracy.historical_samples}</dd></div>

        </dl>

      </div>

      {forecast?.model_version ? (

        <p className="sdash-muted">Modell: {forecast.model_version}</p>

      ) : null}

      {accuracy.metrics_insufficient ? (

        <p className="sdash-warn">Otillräcklig historik för kalibrerade mätvärden.</p>

      ) : null}

    </section>

  );

}



export function SolarForecastSummaryPanel({ forecast }: { forecast: SolarForecast | null }) {

  if (!forecast) {

    return (

      <section className="sdash-panel">

        <h2 className="sdash-panel-title">PROGNOS</h2>

        <p className="sdash-muted">Ingen solprognos tillgänglig.</p>

      </section>

    );

  }

  const deviation =

    forecast.forecast_so_far_kwh > 0

      ? forecast.actual_today_kwh - forecast.forecast_so_far_kwh

      : null;

  return (

    <section className="sdash-panel sdash-forecast-summary" data-testid="solar-forecast-summary">

      <h2 className="sdash-panel-title">PROGNOS SAMMANFATTNING</h2>

      <dl className="sdash-stat-list">

        <div><dt>Kvalitet</dt><dd>{forecast.quality}</dd></div>

        <div><dt>Väder</dt><dd>{forecast.weather_summary}</dd></div>

        <div><dt>Peak effekt</dt><dd>{formatSolarKw(forecast.peak_power_w)}</dd></div>

        <div><dt>Avvikelse hittills</dt><dd>{deviation != null ? formatSolarKwh(deviation) : "—"}</dd></div>

        <div><dt>Kvar idag</dt><dd>{formatSolarKwh(forecast.remaining_today_kwh)}</dd></div>

      </dl>

    </section>

  );

}



export function SolarPlaceholderSection({ title, text }: { title: string; text: string }) {

  return (

    <section className="sdash-panel">

      <h2 className="sdash-panel-title">{title}</h2>

      <p className="sdash-muted">{text}</p>

    </section>

  );

}



export function SolarAttributionFooter({ provider }: { provider: string | null | undefined }) {

  const p = (provider ?? "").toLowerCase();

  const label = p.includes("dmi") ? "DMI" : p.includes("smhi") ? "SMHI" : provider ?? "—";

  return (

    <footer className="sdash-attribution" data-testid="solar-attribution">

      Prognos baserad på väderdata från {label}.

    </footer>

  );

}


