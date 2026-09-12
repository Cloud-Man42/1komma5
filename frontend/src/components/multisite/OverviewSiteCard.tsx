import Link from "next/link";
import type { MultiSiteSiteEntry } from "@/lib/multiSiteApi";

function fmtKw(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(1)} kW`;
}

export function OverviewSiteCard({ site, color }: { site: MultiSiteSiteEntry; color: string }) {
  const gridLabel =
    site.live.gridExportPowerKw && site.live.gridExportPowerKw > 0
      ? `Export ${fmtKw(site.live.gridExportPowerKw)}`
      : site.live.gridImportPowerKw && site.live.gridImportPowerKw > 0
        ? `Import ${fmtKw(site.live.gridImportPowerKw)}`
        : "Nät —";

  return (
    <article className="ms-site-card" style={{ borderLeftColor: color, borderLeftWidth: 4, borderLeftStyle: "solid" }}>
      <h3>
        <span className="ms-site-card-dot" style={{ background: color }} aria-hidden="true" />
        {site.name}
      </h3>
      <p className="muted">
        Status: {site.health}
        {site.healthDetail ? ` — ${site.healthDetail}` : ""}
      </p>
      {!site.available ? <p className="error-text">{site.error ?? "Ingen data"}</p> : null}
      <div className="ms-site-card-meta">
        <span>Sol: {fmtKw(site.live.solarPowerKw)}</span>
        <span>Förbrukning: {fmtKw(site.live.consumptionPowerKw)}</span>
        <span>Batteri: {site.live.batterySocPercent != null ? `${site.live.batterySocPercent}%` : "—"}</span>
        <span>Nät: {gridLabel}</span>
        <span>Sol idag: {site.today.solarKwh != null ? `${site.today.solarKwh.toFixed(1)} kWh` : "—"}</span>
        <span>Förbrukning idag: {site.today.consumptionKwh != null ? `${site.today.consumptionKwh.toFixed(1)} kWh` : "—"}</span>
      </div>
      <Link href={`/sites/${site.slug}?from=overview`} className="ms-btn-primary">
        Öppna anläggning
      </Link>
    </article>
  );
}
