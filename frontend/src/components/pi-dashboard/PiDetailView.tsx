"use client";

import { useEffect, useState } from "react";
import type { DisplayOverview, PiConnectionState } from "@/lib/displayOverview";
import { PiBackButton } from "./PiBackButton";
import { PiConnectionBanner } from "./PiConnectionBanner";
import { PI_HEIGHT, PI_WIDTH } from "./PiDashboard";
import { PiDetailChart, PiDetailTiles } from "./piDetailContent";
import { PiHomeButton } from "./PiHomeButton";
import { IconCloudSun } from "./PiIcons";
import { MISSING, formatClockHms, formatHeaderDate } from "./piDashboardFormatters";
import { PI_SECTION_META, type PiSection } from "./piSections";

const DEFAULT_TZ = "Europe/Stockholm";

function useFitScale() {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const update = () =>
      setScale(Math.min(window.innerWidth / PI_WIDTH, window.innerHeight / PI_HEIGHT));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return scale;
}

function PiDetailHeader({
  slug,
  section,
  data,
  connection,
  nowOverride,
}: {
  slug: string;
  section: PiSection;
  data: DisplayOverview | null;
  connection: PiConnectionState;
  nowOverride?: Date;
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

  return (
    <header className="pi-detail-header">
      <div className="pi-detail-header-left">
        <PiHomeButton slug={slug} />
        <h1 className="pi-detail-title">{PI_SECTION_META[section].title}</h1>
        <PiBackButton />
      </div>
      <div className="pi-detail-header-right">
        <span className={`pi-online ${statusClass}`}>
          <i className="pi-dot" />
          {statusLabel}
        </span>
        <span className="pi-updated pi-detail-updated">
          {formatClockHms(data?.freshness?.updated_at, timezone)}
        </span>
        <div className="pi-weather pi-detail-weather">
          <IconCloudSun />
          <span className="pi-weather-temp">
            {weatherAvailable ? Math.round(weather!.temperature_c as number) : MISSING}
            <span>°C</span>
          </span>
        </div>
        <span className="pi-clock">{stamp.time}</span>
      </div>
    </header>
  );
}

export function PiDetailView({
  slug,
  section,
  data,
  connection,
  nowOverride,
}: {
  slug: string;
  section: PiSection;
  data: DisplayOverview | null;
  connection: PiConnectionState;
  /** Kept for the page contract; the banner reports state, not the raw message. */
  error?: string | null;
  nowOverride?: Date;
}) {
  const scale = useFitScale();
  const hasChart = section === "solar" || section === "energy" || section === "battery" || section === "grid" || section === "economy";

  return (
    <div className="pi-viewport">
      <div className="pi-frame pi-detail-frame" style={{ ["--pi-fit" as string]: scale }}>
        <PiConnectionBanner connection={connection} freshness={data?.freshness} />
        <div className={`pi-detail pi-detail-section-${section}`}>
          <PiDetailHeader
            slug={slug}
            section={section}
            data={data}
            connection={connection}
            nowOverride={nowOverride}
          />
          <PiDetailTiles section={section} data={data} />
          {hasChart ? (
            <section className="pi-detail-chart" aria-label="Diagram">
              <PiDetailChart section={section} data={data} />
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
