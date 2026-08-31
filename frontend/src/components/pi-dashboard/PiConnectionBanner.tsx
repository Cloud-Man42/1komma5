"use client";

import type { DisplayOverview, PiConnectionState } from "@/lib/displayOverview";
import { formatDataAge } from "./piDashboardFormatters";

/**
 * A reachable API is not the same as live data: a site with no Heartbeat mapping
 * answers happily with readings that are days old. The banner therefore reports
 * staleness from the payload, not just whether the fetch succeeded.
 */
export function PiConnectionBanner({
  connection,
  freshness,
}: {
  connection: PiConnectionState;
  freshness?: DisplayOverview["freshness"] | null;
}) {
  if (connection !== "CONNECTED") {
    const reconnecting = connection === "RECONNECTING";
    return (
      <div className={`pi-banner ${reconnecting ? "is-reconnecting" : "is-offline"}`} role="status">
        {reconnecting ? "Återansluter till EMIC…" : "Ingen kontakt med EMIC"}
      </div>
    );
  }

  if (!freshness?.stale) return null;

  const age = formatDataAge(freshness.data_age_seconds);
  return (
    <div className="pi-banner is-stale" role="status">
      {age ? `Inaktuella värden — ${age} sedan senaste mätning` : "Inaktuella värden"}
    </div>
  );
}
