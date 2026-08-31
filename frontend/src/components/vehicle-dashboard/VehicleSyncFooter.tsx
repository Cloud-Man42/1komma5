import { formatRelativeTime } from "@/lib/format";

type Props = {
  lastUpdateIso: string | null;
  signalStrength: string;
  refreshIntervalSec: number;
  connectionState: string | null;
  onSync: () => void;
  syncing: boolean;
};

export function VehicleSyncFooter({
  lastUpdateIso,
  signalStrength,
  refreshIntervalSec,
  connectionState,
  onSync,
  syncing,
}: Props) {
  const lastContact = lastUpdateIso ? formatRelativeTime(lastUpdateIso) : "—";

  return (
    <footer className="vdash-sync-footer" data-testid="vehicle-sync-footer">
      <div className="vdash-sync-left">
        <svg viewBox="0 0 32 32" className="vdash-mercedes-logo" aria-hidden="true">
          <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <path d="M16 4v24M6 12l20 8M26 12L6 20" fill="none" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        <span>Ansluten via Mercedes me API</span>
      </div>
      <div className="vdash-sync-center">
        <span className="vdash-sync-dot" aria-hidden="true" />
        Senast kontakt {lastContact}
      </div>
      <div className="vdash-sync-signal">
        <span className="vdash-signal-bars" aria-hidden="true">
          <i /><i /><i /><i />
        </span>
        {connectionState ?? "—"} · Signalstyrka{" "}
        <strong className="vdash-signal-good">{signalStrength}</strong>
      </div>
      <div className="vdash-sync-right">
        <span className="vdash-sync-refresh-label">Datauppdatering {refreshIntervalSec} sek intervall</span>
        <button type="button" className="vdash-sync-btn" onClick={onSync} disabled={syncing}>
          {syncing ? "Synkar…" : "Synkronisera nu"}
        </button>
      </div>
    </footer>
  );
}
