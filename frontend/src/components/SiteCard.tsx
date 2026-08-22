import Link from "next/link";
import { EnergyFlowDiagram } from "@/components/EnergyFlowDiagram";
import { Site, formatWatts } from "@/lib/api";

interface SiteCardProps {
  site: Site;
}

export function SiteCard({ site }: SiteCardProps) {
  const reading = site.latest_reading;
  return (
    <Link href={`/sites/${site.slug}`} className="card">
      <h2>{site.name}</h2>
      <p className="muted">{site.timezone}</p>
      {reading ? (
        <>
          <EnergyFlowDiagram reading={reading} size="compact" siteSlug={site.slug} />
          <dl className="metrics">
          <div>
            <dt>Solar</dt>
            <dd>{formatWatts(reading.solar_production_w)}</dd>
          </div>
          <div>
            <dt>Consumption</dt>
            <dd>{formatWatts(reading.consumption_w)}</dd>
          </div>
          <div>
            <dt>Battery</dt>
            <dd>{reading.battery_soc_pct.toFixed(0)}%</dd>
          </div>
          <div>
            <dt>Grid import</dt>
            <dd>{formatWatts(reading.grid_import_w)}</dd>
          </div>
        </dl>
        </>
      ) : (
        <p className="muted">No readings yet — start the collector.</p>
      )}
    </Link>
  );
}
