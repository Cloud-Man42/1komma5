import Link from "next/link";
import type { VehicleIntegrationStatus, VehicleListItem } from "@/lib/api";
import { MercedesIntegrationPanel } from "@/components/MercedesIntegrationPanel";
import { connectionLabel, healthLabelSv } from "./vehicleDashboardHelpers";

export function VehicleSettingsSection({
  siteSlug,
  integration,
  vehicle,
}: {
  siteSlug: string;
  integration: VehicleIntegrationStatus | null;
  vehicle: VehicleListItem | null;
}) {
  if (!integration) {
    return (
      <section className="vdash-section" data-testid="vehicle-section-settings">
        <h2 className="vdash-section-title">Inställningar</h2>
        <p className="vdash-muted">Laddar integrationsinställningar…</p>
      </section>
    );
  }

  return (
    <section className="vdash-section" data-testid="vehicle-section-settings">
      <h2 className="vdash-section-title">Inställningar</h2>
      <p className="vdash-section-sub">Mercedes me och EMIC fordonsintegration</p>

      <div className="vdash-settings-grid">
        <div className="vdash-card">
          <header className="vdash-card-header"><h2>INTEGRATION</h2></header>
          <dl className="vdash-settings-dl">
            <div><dt>Status</dt><dd>{integration.enabled ? "Aktiverad" : "Inaktiverad"}</dd></div>
            <div><dt>Anslutning</dt><dd>{connectionLabel(integration.connection_state)}</dd></div>
            <div><dt>Hälsa</dt><dd>{healthLabelSv(integration.health)}</dd></div>
            <div><dt>Kommandon</dt><dd>{integration.commands_enabled ? "Aktiverade" : "Avstängda"}</dd></div>
            <div><dt>Användare</dt><dd>{integration.username || "—"}</dd></div>
            <div><dt>Region</dt><dd>{integration.region}</dd></div>
          </dl>
        </div>

        {vehicle ? (
          <div className="vdash-card">
            <header className="vdash-card-header"><h2>FORDON</h2></header>
            <dl className="vdash-settings-dl">
              <div><dt>Namn</dt><dd>{vehicle.display_name}</dd></div>
              <div><dt>Modell</dt><dd>{vehicle.manufacturer} {vehicle.model}</dd></div>
              <div><dt>VIN</dt><dd>{vehicle.masked_vin ?? "—"}</dd></div>
              <div><dt>Aktiverad</dt><dd>{vehicle.enabled ? "Ja" : "Nej"}</dd></div>
            </dl>
          </div>
        ) : null}
      </div>

      <MercedesIntegrationPanel siteSlug={siteSlug} status={integration} />

      <Link href="/config" className="vdash-config-link">
        Öppna fullständig konfiguration →
      </Link>
    </section>
  );
}
