"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import type { MobileSummaryResponse } from "@/lib/mobileApi";
import { formatFlowPowerFromKw } from "@/lib/multiSiteFlowFormat";
import { MobileSiteDetailCard } from "@/components/mobile/MobileSiteDetailCard";
import { TableSkeleton } from "@/components/admin-ui";

const SolarOverview = dynamic(
  () => import("@/components/solar-dashboard/SolarOverview").then((m) => m.SolarOverview),
  { ssr: false, loading: () => <TableSkeleton rows={6} /> },
);

const EconomyOverview = dynamic(
  () => import("@/components/economy-dashboard/EconomyOverview").then((m) => m.EconomyOverview),
  { ssr: false, loading: () => <TableSkeleton rows={6} /> },
);

function fmtKw(kw: number | null | undefined): string {
  if (kw == null) return "—";
  return formatFlowPowerFromKw(kw);
}

function fmtKwh(kwh: number | null | undefined): string {
  if (kwh == null) return "—";
  return `${kwh.toFixed(1)} kWh`;
}

export function MobileSolarView({ data, slugs }: { data: MobileSummaryResponse; slugs: string[] }) {
  const a = data.aggregate;
  if (slugs.length === 1) {
    return (
      <div className="mobile-embed-view">
        <SolarOverview siteSlug={slugs[0]!} />
      </div>
    );
  }
  return (
    <>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">All sites now</p>
        <div className="mobile-stat-grid">
          <div><span>Solar</span><strong>{fmtKw(a.solarPowerKw)}</strong></div>
          <div><span>Today</span><strong>{fmtKwh(a.solarTodayKwh)}</strong></div>
        </div>
      </section>
      {data.sites.map((site) => (
        <MobileSiteDetailCard key={site.slug} site={site} />
      ))}
      {slugs.map((slug) => (
        <Link key={slug} href={`/sites/${slug}/solar`} className="mobile-hub-link mobile-drill-link">
          {data.sites.find((s) => s.slug === slug)?.name ?? slug} — full solar view →
        </Link>
      ))}
    </>
  );
}

export function MobileBatteryView({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  return (
    <>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">Battery storage</p>
        <div className="mobile-stat-grid">
          <div><span>Stored</span><strong>{fmtKwh(a.batteryStoredKwh)}</strong></div>
          <div><span>Capacity</span><strong>{fmtKwh(a.batteryCapacityKwh)}</strong></div>
          <div><span>SoC</span><strong>{a.batterySocPercent != null ? `${Math.round(a.batterySocPercent)}%` : "—"}</strong></div>
          <div><span>Power</span><strong>{fmtKw(a.batteryChargePowerKw ?? a.batteryDischargePowerKw)}</strong></div>
        </div>
      </section>
      {data.sites.map((site) => (
        <article key={site.slug} className="mobile-site-card">
          <h2>{site.name}</h2>
          <div className="mobile-site-card-grid">
            <div><span>SoC</span><strong>{site.live.batterySocPercent != null ? `${Math.round(site.live.batterySocPercent)}%` : "—"}</strong></div>
            <div><span>Power</span><strong>{fmtKw(site.live.batteryPowerKw)}</strong></div>
          </div>
          <Link href={`/sites/${site.slug}/energy`} className="mobile-site-card-btn">Battery details →</Link>
        </article>
      ))}
    </>
  );
}

export function MobileGridView({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  const netKw = (a.gridExportPowerKw ?? 0) - (a.gridImportPowerKw ?? 0);
  return (
    <>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">Grid now</p>
        <div className="mobile-stat-grid">
          <div><span>Import</span><strong>{fmtKw(a.gridImportPowerKw)}</strong></div>
          <div><span>Export</span><strong>{fmtKw(a.gridExportPowerKw)}</strong></div>
          <div><span>Net</span><strong>{netKw >= 0 ? `${fmtKw(netKw)} export` : `${fmtKw(Math.abs(netKw))} import`}</strong></div>
        </div>
      </section>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">Today</p>
        <div className="mobile-stat-grid">
          <div><span>Import</span><strong>{fmtKwh(a.gridImportTodayKwh)}</strong></div>
          <div><span>Export</span><strong>{fmtKwh(a.gridExportTodayKwh)}</strong></div>
        </div>
      </section>
      {data.currencies.length > 0 ? (
        <section className="mobile-card-section">
          <p className="mobile-section-kicker">Cost by currency</p>
          <div className="mobile-currency-list">
            {data.currencies.map((c) => (
              <div key={c.currency} className="mobile-currency-row">
                <span>{c.currency}</span>
                <span>Cost today {c.costToday ?? "—"}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      {data.sites.map((site) => (
        <MobileSiteDetailCard key={site.slug} site={site} />
      ))}
    </>
  );
}

export function MobileConsumptionView({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  return (
    <>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">Load now</p>
        <strong className="mobile-hero-value">{fmtKw(a.consumptionPowerKw)}</strong>
      </section>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">Today</p>
        <strong className="mobile-hero-value">{fmtKwh(a.consumptionTodayKwh)}</strong>
      </section>
      {data.sites.map((site) => (
        <article key={site.slug} className="mobile-site-card">
          <h2>{site.name}</h2>
          <div className="mobile-site-card-grid">
            <div><span>Now</span><strong>{fmtKw(site.live.consumptionPowerKw)}</strong></div>
            <div><span>Today</span><strong>{fmtKwh(site.today.consumptionKwh)}</strong></div>
          </div>
          <Link href={`/sites/${site.slug}/energy`} className="mobile-site-card-btn">History →</Link>
        </article>
      ))}
    </>
  );
}

export function MobileEconomyView({ data, slugs }: { data: MobileSummaryResponse; slugs: string[] }) {
  if (slugs.length === 1) {
    return (
      <div className="mobile-embed-view">
        <EconomyOverview siteSlug={slugs[0]!} />
      </div>
    );
  }
  return (
    <>
      <section className="mobile-card-section">
        <p className="mobile-section-kicker">Cost today (per currency)</p>
        <div className="mobile-currency-list">
          {data.currencies.map((c) => (
            <div key={c.currency} className="mobile-currency-row">
              <span>{c.currency}</span>
              <span>Cost {c.costToday ?? "—"} · Savings {c.savingsToday ?? "—"}</span>
            </div>
          ))}
        </div>
      </section>
      {data.sites.map((site) => (
        <article key={site.slug} className="mobile-site-card">
          <h2>{site.name}</h2>
          <div className="mobile-site-card-grid">
            <div><span>Cost today</span><strong>{site.today.costToday ?? "—"}</strong></div>
            <div><span>Savings</span><strong>{site.today.savingsToday ?? "—"}</strong></div>
          </div>
          <Link href={`/sites/${site.slug}/costs`} className="mobile-site-card-btn">Full economy →</Link>
        </article>
      ))}
    </>
  );
}

export function MobileHistoryView({ data }: { data: MobileSummaryResponse }) {
  const ranges = [
    { label: "Today", hash: "" },
    { label: "7 days", hash: "#historik" },
    { label: "30 days", hash: "#historik" },
  ] as const;
  return (
    <>
      <p className="muted">Open site energy history for charts and date ranges.</p>
      {data.sites.map((site) => (
        <section key={site.slug} className="mobile-hub-group">
          <h2>{site.name}</h2>
          <ul className="mobile-hub-list">
            {ranges.map((r) => (
              <li key={`${site.slug}-${r.label}`}>
                <Link href={`/sites/${site.slug}/energy${r.hash}`} className="mobile-hub-link">
                  {r.label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}

export function MobileForecastView({ slugs, data }: { slugs: string[]; data: MobileSummaryResponse }) {
  return (
    <>
      {slugs.map((slug) => (
        <section key={slug} className="mobile-hub-group">
          <h2>{data.sites.find((s) => s.slug === slug)?.name ?? slug}</h2>
          <ul className="mobile-hub-list">
            <li>
              <Link href={`/sites/${slug}/solar/intelligence`} className="mobile-hub-link">
                Solar forecast & intelligence
              </Link>
            </li>
            <li>
              <Link href={`/sites/${slug}/solar`} className="mobile-hub-link">
                Solar dashboard
              </Link>
            </li>
          </ul>
        </section>
      ))}
    </>
  );
}
