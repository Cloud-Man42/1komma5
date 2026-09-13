"use client";

import { useEffect } from "react";
import { useServerReachability } from "@/lib/useServerReachability";

export function OfflineRecovery() {
  const { status, retry } = useServerReachability();

  useEffect(() => {
    if (status !== "reachable") return;
    window.location.replace("/app");
  }, [status]);

  const detail =
    status === "offline"
      ? "Telefonen har ingen internetanslutning."
      : status === "unreachable"
        ? "EMIC svarar inte. Anslut till hem-WiFi (samma nätverk som servern) eller VPN, acceptera HTTPS-certifikatet om webbläsaren frågar, och försök igen."
        : status === "reachable"
          ? "Anslutning återställd — öppnar EMIC…"
          : "Kontrollerar anslutning till EMIC…";

  return (
    <div className="mobile-offline-page">
      <h1>Offline</h1>
      <p>Live data is unavailable. Connect to the internet and reopen EMIC.</p>
      <p className="muted">Control commands are disabled while offline.</p>
      <p className="mobile-offline-detail" role="status">
        {detail}
      </p>
      <div className="mobile-offline-actions">
        <button type="button" className="btn btn-primary" onClick={() => void retry()} disabled={status === "checking"}>
          {status === "checking" ? "Kontrollerar…" : "Försök igen"}
        </button>
        <a className="btn btn-secondary" href="/login">
          Gå till inloggning
        </a>
      </div>
    </div>
  );
}
