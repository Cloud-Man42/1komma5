"use client";

import { useState } from "react";
import { runSpaCleaningNow } from "@/lib/api";
import type { SpaControlConfig, SpaStatus } from "@/lib/api";

export function SpaQuickControls({
  siteSlug,
  status,
  control,
  onChanged,
}: {
  siteSlug: string;
  status: SpaStatus;
  control: SpaControlConfig | null;
  onChanged?: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [messageIsError, setMessageIsError] = useState(false);

  const smartControlEnabled = control?.smart_control_enabled ?? false;
  const cleaningBlockedReason = !smartControlEnabled
    ? "Aktivera smartstyrning i schemat för att starta filtercykler."
    : null;

  async function runAction(id: string, fn: () => Promise<{ success: boolean; message: string }>) {
    setBusy(id);
    setMessage(null);
    setMessageIsError(false);
    try {
      const result = await fn();
      setMessage(result.message);
      setMessageIsError(!result.success);
      if (result.success) {
        onChanged?.();
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Kunde inte utföra åtgärden.");
      setMessageIsError(true);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="sdash-panel sdash-controls-panel">
      <h2 className="sdash-panel-title">SNABBKONTROLLER</h2>
      <div className="sdash-controls-stack">
        <button type="button" className="sdash-control-btn" disabled={busy != null}>
          ↑ Öka temperatur
        </button>
        <button type="button" className="sdash-control-btn" disabled={busy != null}>
          ↓ Sänk temperatur
        </button>
        <button type="button" className="sdash-control-btn" disabled={busy != null}>
          ⚡ Boost-läge
          <span>Starta nu</span>
        </button>
        <button
          type="button"
          className="sdash-control-btn"
          disabled={busy != null || Boolean(cleaningBlockedReason)}
          title={cleaningBlockedReason ?? undefined}
          onClick={() => void runAction("clean", () => runSpaCleaningNow(siteSlug))}
        >
          🔄 Rengöringscykel
          <span>{busy === "clean" ? "Skickar…" : "Starta nu"}</span>
        </button>
        <button type="button" className="sdash-control-btn sdash-control-btn-danger" disabled={!status.online || busy != null}>
          ⏻ Stäng av spa
        </button>
      </div>
      {cleaningBlockedReason ? <p className="sdash-muted">{cleaningBlockedReason}</p> : null}
      {message ? (
        <p className={messageIsError ? "sdash-schedule-error" : "sdash-schedule-success"}>{message}</p>
      ) : null}
    </section>
  );
}
