"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ChargeAmpsConfig,
  ChargingReadiness,
  HeartbeatConfig,
  Site,
  fetchChargeAmpsConfig,
  fetchChargingReadiness,
  fetchHeartbeatConfig,
  fetchSites,
} from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";

type StatusLevel = "ok" | "warn" | "bad" | "neutral";

function StatusBadge({ level, label }: { level: StatusLevel; label: string }) {
  return <span className={`config-badge config-badge-${level === "ok" ? "ok" : level === "warn" ? "warn" : level === "bad" ? "bad" : "neutral"}`}>{label}</span>;
}

function heartbeatLevel(config: HeartbeatConfig | null): { level: StatusLevel; label: string; body: string } {
  if (!config) {
    return { level: "neutral", label: "Laddar", body: "Hämtar Heartbeat-status…" };
  }
  if (config.implementation_status === "configured" || config.connection_type === "mock") {
    return {
      level: "ok",
      label: "OK",
      body: `${config.connection_type_label} · ${config.contacting_component}`,
    };
  }
  if (config.implementation_status === "not_configured") {
    return { level: "bad", label: "Saknas", body: "Heartbeat är inte konfigurerad." };
  }
  return { level: "warn", label: "Varning", body: config.implementation_status };
}

function chargeAmpsLevel(config: ChargeAmpsConfig | null): { level: StatusLevel; label: string; body: string } {
  if (!config) {
    return { level: "neutral", label: "Laddar", body: "Hämtar Charge Amps-status…" };
  }
  if (config.ready) {
    return { level: "ok", label: "Redo", body: `Provider: ${config.effective_provider}` };
  }
  return { level: "warn", label: "Ej redo", body: config.notes[0] ?? "Charge Amps saknar konfiguration." };
}

function readinessLevel(readiness: ChargingReadiness | null): { level: StatusLevel; label: string; body: string } {
  if (!readiness) {
    return { level: "neutral", label: "Laddar", body: "Hämtar laddningsstatus…" };
  }
  if (readiness.ready) {
    return {
      level: "ok",
      label: "Redo",
      body: `${readiness.active_bridge_chargers} aktiva bridge-laddboxar`,
    };
  }
  const issueCount = readiness.issues.length;
  return {
    level: issueCount > 0 ? "bad" : "warn",
    label: issueCount > 0 ? `${issueCount} problem` : "Ej redo",
    body: readiness.issues[0]?.message ?? readiness.notes[0] ?? "Smart laddning är inte redo.",
  };
}

function sitesLevel(sites: Site[] | null): { level: StatusLevel; label: string; body: string } {
  if (!sites) {
    return { level: "neutral", label: "Laddar", body: "Hämtar anläggningar…" };
  }
  if (sites.length === 0) {
    return { level: "warn", label: "Tomt", body: "Inga anläggningar skapade ännu." };
  }
  const missingHeartbeat = sites.filter((site) => !site.external_system_id).length;
  if (missingHeartbeat > 0) {
    return {
      level: "warn",
      label: `${sites.length} st`,
      body: `${missingHeartbeat} saknar Heartbeat system-ID`,
    };
  }
  return { level: "ok", label: `${sites.length} st`, body: "Alla anläggningar har Heartbeat-ID" };
}

function adminLevel(): { level: StatusLevel; label: string; body: string } {
  const token = getAdminToken();
  if (token) {
    return { level: "ok", label: "Satt", body: "Admin-token finns i denna webbläsare." };
  }
  return { level: "warn", label: "Saknas", body: "Krävs för display-registrering och vissa admin-API:er." };
}

export function ConfigOverview() {
  const [heartbeat, setHeartbeat] = useState<HeartbeatConfig | null>(null);
  const [chargeAmps, setChargeAmps] = useState<ChargeAmpsConfig | null>(null);
  const [readiness, setReadiness] = useState<ChargingReadiness | null>(null);
  const [sites, setSites] = useState<Site[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchHeartbeatConfig(),
      fetchChargeAmpsConfig(),
      fetchChargingReadiness(),
      fetchSites(),
    ])
      .then(([hb, ca, ready, siteList]) => {
        setHeartbeat(hb);
        setChargeAmps(ca);
        setReadiness(ready);
        setSites(siteList);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda översikt"));
  }, []);

  const cards = [
    { href: "/config/system", title: "System & Heartbeat", ...heartbeatLevel(heartbeat) },
    { href: "/config/system", title: "Charge Amps", ...chargeAmpsLevel(chargeAmps) },
    { href: "/config/system", title: "Smart laddning", ...readinessLevel(readiness) },
    { href: "/config/sites", title: "Anläggningar", ...sitesLevel(sites) },
    { href: "/config/admin", title: "Admin-token", ...adminLevel() },
    { href: "/config/displays", title: "Display & enheter", level: "neutral" as StatusLevel, label: "Konfigurera", body: "Pi-kiosk och Apple/widget-enheter" },
  ];

  return (
    <div data-testid="config-overview">
      <header className="config-page-header">
        <h2 className="config-page-title">Översikt</h2>
        <p className="muted config-page-intro">
          Snabb status för Heartbeat, laddning, anläggningar och admin. Klicka på ett kort för att gå
          till rätt undersida.
        </p>
      </header>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="config-status-grid">
        {cards.map((card) => (
          <Link key={card.title} href={card.href} className="config-status-card">
            <div className="config-status-card-head">
              <h3 className="config-status-card-title">{card.title}</h3>
              <StatusBadge level={card.level} label={card.label} />
            </div>
            <p className="config-status-card-body">{card.body}</p>
          </Link>
        ))}
      </div>

      {readiness && readiness.issues.length > 0 ? (
        <div className="card config-card">
          <h3 className="config-section-title">Aktuella varningar</h3>
          <ul className="config-notes">
            {readiness.issues.map((issue) => (
              <li key={`${issue.site_slug}-${issue.charger_id}-${issue.code}`}>
                {issue.site_slug}/{issue.charger_name}: {issue.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
