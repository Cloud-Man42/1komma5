"use client";

import { useEffect, useState } from "react";
import type { DisplayOverview, PiConnectionState } from "@/lib/displayOverview";
import { IconAlertCircle, IconBrand, IconCheckCircle, IconCloudSun } from "./PiIcons";
import { PiHomeButton } from "./PiHomeButton";
import { MISSING, formatClockHms, formatHeaderDate } from "./piDashboardFormatters";

const DEFAULT_TZ = "Europe/Stockholm";

export function PiHeader({
  slug,
  data,
  connection,
  nowOverride,
  isHome = true,
}: {
  slug: string;
  data: DisplayOverview | null;
  connection: PiConnectionState;
  /** Fixed clock used by the visual-comparison preview and tests. */
  nowOverride?: Date;
  isHome?: boolean;
}) {
  const timezone = data?.site?.timezone ?? DEFAULT_TZ;
  const [tick, setTick] = useState<Date | null>(nowOverride ?? null);

  useEffect(() => {
    if (nowOverride) return;
    setTick(new Date());
    const timer = window.setInterval(() => setTick(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, [nowOverride]);

  const now = nowOverride ?? tick;
  const stamp = now ? formatHeaderDate(now, timezone) : { weekday: "", date: MISSING, time: "--:--" };
  const stale = data?.freshness?.stale === true;

  const statusClass =
    connection === "CONNECTED" ? (stale ? "is-stale" : "") : connection === "RECONNECTING" ? "is-stale" : "is-offline";
  const statusLabel =
    connection === "CONNECTED" ? (stale ? "STALE" : "ONLINE") : connection === "RECONNECTING" ? "ÅTERANSLUTER" : "OFFLINE";

  const weather = data?.weather;
  const weatherAvailable = weather?.available === true && weather.temperature_c != null;

  const sys = data?.system_status;
  const sysHealthy = sys?.healthy !== false;
  const sysText = sys?.status_sv ?? "--";
  const sysDetail = sys?.detail_sv ?? "Väntar på data.";

  return (
    <header className="pi-header">
      <div className="pi-header-left">
        <PiHomeButton slug={slug} isHome={isHome} />
        <div className="pi-header-brand">
          <IconBrand className="pi-brand-mark" />
          <div>
            <span className="pi-brand-name">EMIC</span>
            <span className="pi-brand-sub">ENERGY INTELLIGENCE</span>
          </div>
        </div>
        <span className="pi-header-sep pi-header-sep-brand" aria-hidden />
        <span className="pi-site-name">{data?.site?.name ?? "Åkarp"}</span>
        <span className={`pi-online ${statusClass}`}>
          <i className="pi-dot" />
          {statusLabel}
        </span>
        <span
          className={`pi-sys-pill${sysHealthy ? "" : " is-bad"}`}
          title={sysDetail}
        >
          {sysHealthy ? <IconCheckCircle /> : <IconAlertCircle />}
          <span>{sysText}</span>
        </span>
        <span className="pi-updated">
          Sist uppdaterad: {formatClockHms(data?.freshness?.updated_at, timezone)}
        </span>
      </div>

      <div className="pi-header-right">
        <div className="pi-weather">
          <IconCloudSun />
          <div>
            <span className="pi-weather-temp">
              {weatherAvailable ? Math.round(weather.temperature_c as number) : MISSING}
              <span>°C</span>
            </span>
            <span className="pi-weather-label">
              {weatherAvailable ? (weather.label_sv ?? MISSING) : "Data saknas"}
            </span>
          </div>
        </div>

        <span className="pi-header-sep" />

        <div className="pi-date">
          <span className="pi-date-weekday">{stamp.weekday}</span>
          <span className="pi-date-full">{stamp.date}</span>
        </div>

        <span className="pi-clock">{stamp.time}</span>
      </div>
    </header>
  );
}
