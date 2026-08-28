import type { SpaHealth, SpaStatus } from "@/lib/api";
import { isHeaterLive, isUvActive, sensorStatusLabel } from "./spaDashboardHelpers";

function StatusChip({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="sdash-footer-chip">
      <span>{label}</span>
      <strong>{value}</strong>
      {ok != null ? <em className={ok ? "is-ok" : "is-warn"}>{ok ? "OK" : "—"}</em> : null}
    </div>
  );
}

export function SpaStatusFooter({
  status,
  health,
  onShowSensors,
}: {
  status: SpaStatus;
  health: SpaHealth | null;
  onShowSensors?: () => void;
}) {
  const wifi = status.online ? "Stark" : "Svag";
  const lock = status.filter_status?.toLowerCase().includes("open") ? "Öppet" : "Stängt";
  const heating = isHeaterLive(status);
  const frost = heating ? "Aktivt" : "Vila";

  return (
    <footer className="sdash-footer">
      <StatusChip label="Vattenkvalitet" value={sensorStatusLabel(null)} />
      <StatusChip label="Ozonator" value={sensorStatusLabel(null)} />
      <StatusChip label="UV-rening" value={sensorStatusLabel(isUvActive(status) ? true : false)} />
      <StatusChip label="Wifi-signal" value={wifi} />
      <StatusChip label="Lock" value={lock} />
      <StatusChip label="Frostskydd" value={frost} />
      <button type="button" className="sdash-footer-link" onClick={onShowSensors}>
        Visa alla sensorer
      </button>
      {health?.integration_degraded ? (
        <span className="sdash-footer-warn">{health.integration_degraded_message_sv}</span>
      ) : null}
    </footer>
  );
}
