import Link from "next/link";
import { Site } from "@/lib/api";
import { formatPercent, formatPower } from "@/lib/format";
import { StatusBadge } from "@/components/dashboard";

export function SiteOverviewCard({ site }: { site: Site }) {
  const reading = site.latest_reading;
  const statusTone = reading ? "success" : "warning";
  const statusLabel = reading ? "Normal" : "Ingen data";

  return (
    <Link href={`/sites/${site.slug}`} className="site-overview-card">
      <h2 className="site-overview-card-title">{site.name}</h2>
      <p className="muted">{site.timezone}</p>
      {reading ? (
        <dl className="metrics" style={{ marginTop: "var(--space-4)" }}>
          <div>
            <dt>Sol</dt>
            <dd>{formatPower(reading.solar_production_w)}</dd>
          </div>
          <div>
            <dt>Batteri</dt>
            <dd>{formatPercent(reading.battery_soc_pct)}</dd>
          </div>
        </dl>
      ) : (
        <p className="muted" style={{ marginTop: "var(--space-4)" }}>
          Inga mätningar ännu
        </p>
      )}
      <div className="site-overview-card-status">
        <StatusBadge label={statusLabel} tone={statusTone} />
      </div>
    </Link>
  );
}
