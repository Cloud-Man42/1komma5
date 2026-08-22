"use client";



import { useEffect, useMemo, useState } from "react";

import {

  CartesianGrid,

  Legend,

  Line,

  LineChart,

  ResponsiveContainer,

  Tooltip,

  XAxis,

  YAxis,

} from "recharts";

import { AggregatedReading, Reading, SolarForecastPoint, isAggregated } from "@/lib/api";



interface EnergyChartProps {

  readings: (Reading | AggregatedReading)[];

  forecastPoints?: SolarForecastPoint[];

}



interface ChartRow {

  time: string;

  sortKey: number;

  solar: number | null;

  consumption: number | null;

  battery: number | null;

  forecastSolar: number | null;

  forecastLower: number | null;

  forecastUpper: number | null;

}



function formatChartTime(iso: string): string {

  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

}



export function mergeChartData(

  readings: (Reading | AggregatedReading)[],

  forecastPoints: SolarForecastPoint[],

): ChartRow[] {

  const rows = new Map<string, ChartRow>();



  for (const reading of readings) {

    const iso = isAggregated(reading) ? reading.bucket_start : reading.recorded_at;

    const time = formatChartTime(iso);

    rows.set(time, {

      time,

      sortKey: new Date(iso).getTime(),

      solar: Math.round(reading.solar_production_w),

      consumption: Math.round(reading.consumption_w),

      battery: Math.round(reading.battery_soc_pct),

      forecastSolar: null,

      forecastLower: null,

      forecastUpper: null,

    });

  }



  for (const point of forecastPoints) {

    const time = formatChartTime(point.timestamp);

    const existing = rows.get(time) ?? {

      time,

      sortKey: new Date(point.timestamp).getTime(),

      solar: null,

      consumption: null,

      battery: null,

      forecastSolar: null,

      forecastLower: null,

      forecastUpper: null,

    };

    rows.set(time, {

      ...existing,

      forecastSolar: Math.round(point.corrected_power_w),

      forecastLower: Math.round(point.lower_bound_power_w),

      forecastUpper: Math.round(point.upper_bound_power_w),

    });

  }



  return Array.from(rows.values()).sort((a, b) => a.sortKey - b.sortKey);

}



function useIsMobile(breakpoint = 640) {

  const [isMobile, setIsMobile] = useState(false);



  useEffect(() => {

    const media = window.matchMedia(`(max-width: ${breakpoint}px)`);

    const update = () => setIsMobile(media.matches);

    update();

    media.addEventListener("change", update);

    return () => media.removeEventListener("change", update);

  }, [breakpoint]);



  return isMobile;

}



export function EnergyChart({ readings, forecastPoints = [] }: EnergyChartProps) {

  const isMobile = useIsMobile();

  const merged = useMemo(

    () => mergeChartData(readings, forecastPoints),

    [readings, forecastPoints],

  );

  const hasForecast = forecastPoints.length > 0;



  if (merged.length === 0) {

    return <p className="muted">Ingen historisk data ännu.</p>;

  }



  const chartHeight = isMobile ? 260 : 320;

  const tickStyle = { fill: "#94a3b8", fontSize: isMobile ? 10 : 12 };

  const labelStyle = { color: "#e2e8f0", fontSize: isMobile ? 12 : 14 };



  return (

    <div className="chart">

      <div className="chart-inner">

        <ResponsiveContainer width="100%" height={chartHeight}>

          <LineChart

            data={merged}

            margin={

              isMobile

                ? { top: 8, right: 4, left: -18, bottom: 4 }

                : { top: 8, right: 16, left: 0, bottom: 8 }

            }

          >

            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

            <XAxis

              dataKey="time"

              tick={tickStyle}

              interval={isMobile ? "preserveStartEnd" : "equidistantPreserveStart"}

              angle={isMobile ? -35 : 0}

              textAnchor={isMobile ? "end" : "middle"}

              height={isMobile ? 50 : 30}

            />

            <YAxis

              yAxisId="power"

              tick={tickStyle}

              width={isMobile ? 42 : 56}

              tickFormatter={(v) => (Math.abs(v) >= 1000 ? `${v / 1000}k` : String(v))}

            />

            <YAxis

              yAxisId="battery"

              orientation="right"

              domain={[0, 100]}

              tick={tickStyle}

              width={isMobile ? 32 : 40}

              tickFormatter={(v) => `${v}%`}

            />

            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} labelStyle={labelStyle} />

            <Legend

              wrapperStyle={{ fontSize: isMobile ? 11 : 13, paddingTop: isMobile ? 4 : 8 }}

              verticalAlign="bottom"

            />

            <Line yAxisId="power" type="monotone" dataKey="solar" name="Solar (mätt)" stroke="#f59e0b" dot={false} strokeWidth={2} />

            {hasForecast && (

              <>

                <Line

                  yAxisId="power"

                  type="monotone"

                  dataKey="forecastLower"

                  name="Prognos (min)"

                  stroke="#92400e"

                  strokeDasharray="4 4"

                  strokeOpacity={0.55}

                  dot={false}

                  strokeWidth={1.5}

                  connectNulls={false}

                />

                <Line

                  yAxisId="power"

                  type="monotone"

                  dataKey="forecastSolar"

                  name="Solar (prognos)"

                  stroke="#fbbf24"

                  strokeDasharray="6 4"

                  dot={false}

                  strokeWidth={2}

                  connectNulls={false}

                />

                <Line

                  yAxisId="power"

                  type="monotone"

                  dataKey="forecastUpper"

                  name="Prognos (max)"

                  stroke="#92400e"

                  strokeDasharray="4 4"

                  strokeOpacity={0.55}

                  dot={false}

                  strokeWidth={1.5}

                  connectNulls={false}

                />

              </>

            )}

            <Line yAxisId="power" type="monotone" dataKey="consumption" name="Consumption" stroke="#3b82f6" dot={false} strokeWidth={2} />

            <Line yAxisId="battery" type="monotone" dataKey="battery" name="Battery %" stroke="#10b981" dot={false} strokeWidth={2} />

          </LineChart>

        </ResponsiveContainer>

      </div>

    </div>

  );

}


