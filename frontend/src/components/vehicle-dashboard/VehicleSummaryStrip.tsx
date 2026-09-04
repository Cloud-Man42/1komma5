import type { VehicleDisplay } from "./vehicleDashboardHelpers";
import { formatGps, formatSek, healthLabelSv } from "./vehicleDashboardHelpers";

export function VehicleSummaryStrip({ display, siteName }: { display: VehicleDisplay; siteName: string }) {
  return (
    <section className="vdash-summary-strip" data-testid="vehicle-summary-strip">
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">VIN</span>
        <strong>{display.maskedVin}</strong>
        <small>{display.manufacturer} {display.model}</small>
      </div>
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">Senaste laddning</span>
        <strong>
          {display.lastChargeKwh != null ? `+${display.lastChargeKwh.toFixed(1)} kWh` : "—"}
        </strong>
        <small>
          {display.lastChargeTime} · {display.lastChargeDuration}
        </small>
      </div>
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">Total laddenergi</span>
        <strong>{display.totalEnergyKwh.toFixed(1)} kWh</strong>
        <small>{display.sessions.length} sessioner</small>
      </div>
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">Total besparing</span>
        <strong>{formatSek(display.totalSavingsKr)}</strong>
        <small>EMIC-attribuering</small>
      </div>
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">Position</span>
        <strong>{display.locationTitle ?? "—"}</strong>
        <small>{display.locationSubtitle ?? formatGps(display.latitude, display.longitude) ?? "Ingen GPS"}</small>
      </div>
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">Garage</span>
        <strong>{siteName}</strong>
        <small>Hemmaplats</small>
      </div>
      <div className="vdash-summary-item">
        <span className="vdash-summary-label">Integration</span>
        <strong>{healthLabelSv(display.integration?.health)}</strong>
        <small className="vdash-summary-ok">Mercedes me</small>
      </div>
    </section>
  );
}
