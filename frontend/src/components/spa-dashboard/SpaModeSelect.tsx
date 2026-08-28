"use client";

import { useState } from "react";
import { updateSpaControlConfig, type SpaControlConfig } from "@/lib/api";
import { SPA_STRATEGY_OPTIONS, strategyHintSv, strategyLabelSv } from "./spaDashboardHelpers";

export function SpaModeSelect({
  siteSlug,
  control,
  onChanged,
}: {
  siteSlug: string;
  control: SpaControlConfig | null;
  onChanged?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentStrategy = control?.strategy ?? "";
  const strategyHint = strategyHintSv(currentStrategy);
  const options =
    currentStrategy && !SPA_STRATEGY_OPTIONS.some((option) => option.id === currentStrategy)
      ? [{ id: currentStrategy, label: strategyLabelSv(currentStrategy) }, ...SPA_STRATEGY_OPTIONS]
      : [...SPA_STRATEGY_OPTIONS];

  async function handleChange(nextStrategy: string) {
    if (!control || nextStrategy === currentStrategy) return;
    setBusy(true);
    setError(null);
    try {
      await updateSpaControlConfig(siteSlug, { strategy: nextStrategy });
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte byta SPAläge");
    } finally {
      setBusy(false);
    }
  }

  return (
    <label className="sdash-select-wrap">
      <span>SPALÄGE</span>
      <select
        value={currentStrategy}
        disabled={!control || busy}
        aria-busy={busy}
        onChange={(event) => void handleChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      {strategyHint ? <span className="sdash-select-hint">{strategyHint}</span> : null}
      {error ? <span className="sdash-select-error">{error}</span> : null}
    </label>
  );
}
