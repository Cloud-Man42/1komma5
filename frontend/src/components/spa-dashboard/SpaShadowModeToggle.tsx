"use client";

import { useState } from "react";
import { updateSpaControlConfig, type SpaControlConfig } from "@/lib/api";
import { shadowModeHintSv } from "./spaDashboardHelpers";

export function SpaShadowModeToggle({
  siteSlug,
  control,
  compact = false,
  onChanged,
}: {
  siteSlug: string;
  control: SpaControlConfig | null;
  compact?: boolean;
  onChanged?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = control?.shadow_mode ?? false;

  async function handleToggle() {
    if (!control || busy) return;
    setBusy(true);
    setError(null);
    try {
      await updateSpaControlConfig(siteSlug, { shadow_mode: !active });
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte uppdatera shadow mode");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={compact ? "sdash-shadow-toggle is-compact" : "sdash-shadow-toggle"}>
      <label className="sdash-shadow-toggle-label">
        <input
          type="checkbox"
          role="switch"
          aria-label="Shadow mode"
          checked={active}
          disabled={!control || busy}
          onChange={() => void handleToggle()}
        />
        <span className="sdash-shadow-toggle-title">
          Shadow mode
          {active ? <em className="sdash-shadow-badge">Aktiv</em> : null}
        </span>
      </label>
      {!compact ? <p className="sdash-muted">{shadowModeHintSv(active)}</p> : null}
      {error ? <p className="sdash-schedule-error">{error}</p> : null}
    </div>
  );
}
