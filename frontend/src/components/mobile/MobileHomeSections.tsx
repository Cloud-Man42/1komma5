"use client";

import Link from "next/link";
import type { MobileSummaryResponse } from "@/lib/mobileApi";
import { formatFlowPowerFromKw } from "@/lib/multiSiteFlowFormat";
import { buildSiteColorMap } from "@/lib/multiSiteSiteColors";

function fmtKw(kw: number | null | undefined): string {
  if (kw == null) return "—";
  return formatFlowPowerFromKw(kw);
}

function fmtKwh(kwh: number | null | undefined): string {
  if (kwh == null) return "—";
  return `${kwh.toFixed(1)} kWh`;
}

export function MobileHeroStatus({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  const batteryKw = (a.batteryDischargePowerKw ?? 0) - (a.batteryChargePowerKw ?? 0);
  const batteryLabel =
    batteryKw > 0.05
      ? `${fmtKw(batteryKw)} discharge`
      : batteryKw < -0.05
        ? `${fmtKw(Math.abs(batteryKw))} charge`
        : "Idle";

  return (
    <section className="mobile-hero" aria-label="Total power now">
      <p className="mobile-section-kicker">Total power now</p>
      <div className="mobile-hero-grid">
        <div className="mobile-hero-item">
          <span className="mobile-hero-label">Consumption</span>
          <strong className="mobile-hero-value">{fmtKw(a.consumptionPowerKw)}</strong>
        </div>
        <div className="mobile-hero-item mobile-accent-solar">
          <span className="mobile-hero-label">Solar</span>
          <strong className="mobile-hero-value">{fmtKw(a.solarPowerKw)}</strong>
        </div>
        <div className="mobile-hero-item mobile-accent-battery">
          <span className="mobile-hero-label">Battery</span>
          <strong className="mobile-hero-value">{batteryLabel}</strong>
        </div>
        <div className="mobile-hero-item mobile-accent-grid">
          <span className="mobile-hero-label">Grid</span>
          <strong className="mobile-hero-value">
            {a.gridImportPowerKw && a.gridImportPowerKw > 0
              ? `${fmtKw(a.gridImportPowerKw)} import`
              : a.gridExportPowerKw && a.gridExportPowerKw > 0
                ? `${fmtKw(a.gridExportPowerKw)} export`
                : "Balanced"}
          </strong>
        </div>
      </div>
    </section>
  );
}

export function MobileEnergyFlow({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  return (
    <section className="mobile-flow" aria-label="Energy flow">
      <p className="mobile-section-kicker">Energy flow</p>
      <div className="mobile-flow-stack">
        <div className="mobile-flow-node mobile-accent-solar">
          <span>Solar</span>
          <strong>{fmtKw(a.solarPowerKw)}</strong>
        </div>
        <div className="mobile-flow-arrow" aria-hidden="true">↓</div>
        <div className="mobile-flow-node">
          <span>Home / Sites</span>
          <strong>{fmtKw(a.consumptionPowerKw)}</strong>
        </div>
        <div className="mobile-flow-row">
          <div className="mobile-flow-node mobile-accent-battery">
            <span>Battery</span>
            <strong>{fmtKw(a.batteryChargePowerKw ?? a.batteryDischargePowerKw)}</strong>
          </div>
          <div className="mobile-flow-node mobile-accent-grid">
            <span>Grid</span>
            <strong>
              {fmtKw(a.gridImportPowerKw)} / {fmtKw(a.gridExportPowerKw)}
            </strong>
          </div>
        </div>
      </div>
    </section>
  );
}

export function MobileDailySummary({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  return (
    <section className="mobile-card-section" aria-label="Today">
      <p className="mobile-section-kicker">Today</p>
      <div className="mobile-stat-grid">
        <div><span>Solar</span><strong>{fmtKwh(a.solarTodayKwh)}</strong></div>
        <div><span>Consumption</span><strong>{fmtKwh(a.consumptionTodayKwh)}</strong></div>
        <div><span>Grid import</span><strong>{fmtKwh(a.gridImportTodayKwh)}</strong></div>
        <div><span>Grid export</span><strong>{fmtKwh(a.gridExportTodayKwh)}</strong></div>
      </div>
      {data.currencies.length > 0 ? (
        <div className="mobile-currency-list">
          {data.currencies.map((c) => (
            <div key={c.currency} className="mobile-currency-row">
              <span>{c.currency}</span>
              <span>
                Cost {c.costToday ?? "—"} · Savings {c.savingsToday ?? "—"}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function MobileBatterySummary({ data }: { data: MobileSummaryResponse }) {
  const a = data.aggregate;
  if (a.batteryCapacityKwh == null) return null;
  const charging = data.sites.filter((s) => (s.live.batteryPowerKw ?? 0) > 0).length;
  const discharging = data.sites.filter((s) => (s.live.batteryPowerKw ?? 0) < 0).length;
  return (
    <section className="mobile-card-section" aria-label="Battery storage">
      <p className="mobile-section-kicker">Battery storage</p>
      <div className="mobile-battery-summary">
        <strong>{fmtKwh(a.batteryStoredKwh)}</strong> stored · {a.batteryCapacityKwh} kWh capacity · {a.batterySocPercent ?? "—"}%
      </div>
      <p className="muted mobile-battery-meta">
        {data.sites.filter((s) => s.live.batterySocPercent != null).length} batteries · {charging} charging · {discharging} discharging
      </p>
      <Link href="/app/energy" className="mobile-link-btn">
        Battery overview
      </Link>
    </section>
  );
}

export function MobileSiteCards({ data }: { data: MobileSummaryResponse }) {
  const colors = buildSiteColorMap(data.sites.map((s) => s.slug));
  return (
    <section className="mobile-card-section" aria-label="Sites">
      <p className="mobile-section-kicker">Sites</p>
      <ul className="mobile-site-cards">
        {data.sites.map((site) => (
          <li key={site.slug}>
            <Link href={`/sites/${site.slug}`} className="mobile-site-card" style={{ borderLeftColor: colors[site.slug] }}>
              <div className="mobile-site-card-head">
                <strong>{site.name}</strong>
                <span className={`mobile-health mobile-health-${site.health}`}>{site.health}</span>
              </div>
              <div className="mobile-site-card-stats">
                <span>Solar {fmtKw(site.live.solarPowerKw)}</span>
                <span>Load {fmtKw(site.live.consumptionPowerKw)}</span>
                <span>Battery {site.live.batterySocPercent ?? "—"}%</span>
                <span>
                  Grid{" "}
                  {site.live.gridExportPowerKw && site.live.gridExportPowerKw > 0
                    ? `Export ${fmtKw(site.live.gridExportPowerKw)}`
                    : site.live.gridImportPowerKw && site.live.gridImportPowerKw > 0
                      ? `Import ${fmtKw(site.live.gridImportPowerKw)}`
                      : "—"}
                </span>
              </div>
              <div className="mobile-site-card-today">Today solar {fmtKwh(site.today.solarKwh)}</div>
              <span className="mobile-site-card-cta">Open →</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function MobileWarnings({ data }: { data: MobileSummaryResponse }) {
  if (!data.warnings.length) return null;
  return (
    <section className="mobile-card-section mobile-warnings" aria-label="Needs attention">
      <p className="mobile-section-kicker">Needs attention</p>
      <ul>
        {data.warnings.map((w, i) => (
          <li key={`${w.slug}-${i}`} className={`mobile-warning mobile-warning-${w.severity}`}>
            <strong>{w.name}</strong>
            <span>{w.message}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function MobileQuickActions({ data }: { data: MobileSummaryResponse }) {
  if (!data.quickActions.length) return null;
  return (
    <section className="mobile-card-section" aria-label="Quick actions">
      <p className="mobile-section-kicker">Quick actions</p>
      <div className="mobile-quick-actions">
        {data.quickActions.map((action) => (
          <Link key={action.id} href={action.route} className="mobile-quick-action">
            {action.label}
          </Link>
        ))}
      </div>
    </section>
  );
}

export function MobileStatusHeader({ data }: { data: MobileSummaryResponse }) {
  const online = data.health.healthy + data.health.degraded;
  const total = data.sites.length;
  return (
    <div className="mobile-status-header">
      <p>
        <strong>{total}</strong> selected · <strong>{online}</strong> online
        {data.health.offline ? ` · ${data.health.offline} offline` : ""}
      </p>
      <p className="muted">MONITOR · CONTROL · OPTIMIZE</p>
    </div>
  );
}
