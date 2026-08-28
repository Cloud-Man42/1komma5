import type { VehicleCapabilities, VehicleHaloCorrelation, VehicleIntegrationStatus } from "@/lib/api";
import { capabilityLabelSv, connectionLabel, formatKw } from "./vehicleDashboardHelpers";

type Props = {
  capabilities: VehicleCapabilities | null;
  integration: VehicleIntegrationStatus | null;
  halo: VehicleHaloCorrelation | null;
  dataQuality: string;
  freshnessLabel: string;
};

export function VehicleStatusPanel({
  capabilities,
  integration,
  halo,
  dataQuality,
  freshnessLabel,
}: Props) {
  const items = [
    { label: "Mercedes me", value: connectionLabel(integration?.connection_state) },
    { label: "Datakvalitet", value: dataQuality },
    { label: "Datastatus", value: freshnessLabel },
    { label: "Läs SoC", value: capabilityLabelSv(capabilities?.can_read_soc) },
    { label: "Läs räckvidd", value: capabilityLabelSv(capabilities?.can_read_range) },
    { label: "Laddkommandon", value: capabilityLabelSv(capabilities?.can_stop_charging) },
  ];

  return (
    <section className="vdash-card" id="status" data-testid="vehicle-status">
      <header className="vdash-card-header">
        <h2>FORDONSSTATUS</h2>
      </header>
      <ul className="vdash-status-list">
        {items.map((item) => (
          <li key={item.label}>
            <span className="vdash-check" aria-hidden="true">✓</span>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </li>
        ))}
      </ul>
      {halo ? (
        <div className="vdash-halo-block" data-testid="vehicle-halo-status">
          <p className="vdash-card-sub">Halo-korrelation</p>
          <ul className="vdash-status-list">
            <li>
              <span className="vdash-check" aria-hidden="true">✓</span>
              <span>Status</span>
              <strong>{halo.status}</strong>
            </li>
            <li>
              <span className="vdash-check" aria-hidden="true">✓</span>
              <span>Confidence</span>
              <strong>{Math.round(halo.confidence * 100)}%</strong>
            </li>
            <li>
              <span className="vdash-check" aria-hidden="true">✓</span>
              <span>Mercedes effekt</span>
              <strong>{formatKw(halo.vehicle_power_kw)}</strong>
            </li>
            <li>
              <span className="vdash-check" aria-hidden="true">✓</span>
              <span>Halo effekt</span>
              <strong>{formatKw(halo.halo_power_kw)}</strong>
            </li>
          </ul>
          {halo.notes ? <p className="vdash-muted">{halo.notes}</p> : null}
        </div>
      ) : null}
      {integration?.last_error ? (
        <p className="vdash-action-msg vdash-action-msg-err">{integration.last_error}</p>
      ) : null}
    </section>
  );
}
