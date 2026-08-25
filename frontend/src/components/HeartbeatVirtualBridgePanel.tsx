"use client";

import { useCallback, useEffect, useState } from "react";

import {
  HeartbeatBridgeDecision,
  HeartbeatBridgeSettings,
  HeartbeatBridgeStatus,
  HeartbeatDiscoveryRunResult,
  HeartbeatDiscoveryRunDetail,
  fetchHeartbeatBridgeDecisions,
  fetchHeartbeatBridgeSettings,
  fetchHeartbeatBridgeStatus,
  fetchHeartbeatDiscoveryRun,
  runHeartbeatDiscovery,
  runHeartbeatReplay,
  runHeartbeatWriteTest,
  updateHeartbeatBridgeSettings,
} from "@/lib/api";

export function HeartbeatVirtualBridgePanel({ siteSlug }: { siteSlug: string }) {
  const [status, setStatus] = useState<HeartbeatBridgeStatus | null>(null);
  const [settings, setSettings] = useState<HeartbeatBridgeSettings | null>(null);
  const [lastRun, setLastRun] = useState<HeartbeatDiscoveryRunResult | null>(null);
  const [runDetail, setRunDetail] = useState<HeartbeatDiscoveryRunDetail | null>(null);
  const [reportText, setReportText] = useState<string | null>(null);
  const [replayText, setReplayText] = useState<string | null>(null);
  const [writeTestResult, setWriteTestResult] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<HeartbeatBridgeDecision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [bridgeStatus, bridgeSettings, recentDecisions] = await Promise.all([
        fetchHeartbeatBridgeStatus(siteSlug),
        fetchHeartbeatBridgeSettings(siteSlug),
        fetchHeartbeatBridgeDecisions(siteSlug),
      ]);
      setStatus(bridgeStatus);
      setSettings(bridgeSettings);
      setDecisions(recentDecisions);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ladda bridge-status");
    }
  }, [siteSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRunDiscovery = async () => {
    setBusy(true);
    setError(null);
    setReportText(null);
    try {
      const result = await runHeartbeatDiscovery(siteSlug);
      setLastRun(result);
      setReportText(result.report_text);
      const detail = await fetchHeartbeatDiscoveryRun(siteSlug, result.run_id);
      setRunDetail(detail);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery misslyckades");
    } finally {
      setBusy(false);
    }
  };

  const onDryRunWrite = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await runHeartbeatWriteTest(siteSlug, true);
      setWriteTestResult(`${result.classification}${result.error ? `: ${result.error}` : ""}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Write test misslyckades");
    } finally {
      setBusy(false);
    }
  };

  const onLiveWrite = async () => {
    if (!window.confirm("Kör minimal Heartbeat write-test? Endast idempotent same-value write.")) return;
    setBusy(true);
    setError(null);
    try {
      await updateHeartbeatBridgeSettings(siteSlug, { write_enabled: true });
      const result = await runHeartbeatWriteTest(siteSlug, false);
      setWriteTestResult(`${result.classification} (HTTP ${result.http_status ?? "?"})`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live write test misslyckades");
    } finally {
      setBusy(false);
    }
  };

  const onReplay = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await runHeartbeatReplay(siteSlug);
      setReplayText(result.report_text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replay misslyckades");
    } finally {
      setBusy(false);
    }
  };

  const toggleSimulation = async () => {
    if (!settings) return;
    const updated = await updateHeartbeatBridgeSettings(siteSlug, {
      simulation_mode: !settings.simulation_mode,
    });
    setSettings(updated);
    await load();
  };

  return (
    <details className="card" open>
      <summary>
        <strong>Heartbeat Virtual EV Bridge</strong>
      </summary>
      <div className="diagnostics-panel" style={{ marginTop: "0.75rem" }}>
        {error ? <p className="error-text">{error}</p> : null}

        {status ? (
          <div className="diagnostics-grid">
            <div>Heartbeat connection: {status.heartbeat_connection}</div>
            <div>EV profile: {status.ev_profile}</div>
            <div>EV ID: {status.ev_id ?? "—"}</div>
            <div>Confidence: {status.confidence_pct != null ? `${status.confidence_pct}%` : "—"}</div>
            <div>Charge Amps Halo: {status.charge_amps_halo}</div>
            <div>Virtual bridge: {status.virtual_bridge}</div>
            <div>Simulation: {status.simulation_mode ? "ENABLED" : "DISABLED"}</div>
            <div>Physical control: {status.physical_control}</div>
            <div>Classification: {status.setup_classification ?? "—"}</div>
          </div>
        ) : null}

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void onRunDiscovery()}>
            RUN HEARTBEAT EV DISCOVERY
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void onDryRunWrite()}>
            Write test (dry-run)
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void onLiveWrite()}>
            TEST HEARTBEAT WRITE
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void onReplay()}>
            Replay 24h
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy || !settings} onClick={() => void toggleSimulation()}>
            Toggle simulation
          </button>
        </div>

        {reportText ? (
          <pre className="diagnostics-subpanel" style={{ whiteSpace: "pre-wrap", marginTop: "0.75rem" }}>
            {reportText}
          </pre>
        ) : null}

        {writeTestResult ? <p className="muted">Write test: {writeTestResult}</p> : null}
        {replayText ? <p className="muted">Replay: {replayText}</p> : null}

        {decisions.length > 0 ? (
          <div style={{ marginTop: "0.75rem" }}>
            <h4>Virtual charger decisions (simulation)</h4>
            <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
              {decisions.slice(0, 10).map((decision, index) => (
                <li key={`${decision.recorded_at}-${index}`}>
                  {decision.recorded_at}: {decision.bridge_state}
                  {decision.heartbeat_mode ? ` · ${decision.heartbeat_mode}` : ""}
                  {decision.ai_decision ? ` · AI ${decision.ai_decision}` : ""}
                  {" — "}
                  {decision.reason}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {runDetail && runDetail.observations.length > 0 ? (
          <div style={{ marginTop: "0.75rem" }}>
            <h4>API observations</h4>
            {runDetail.observations.map((obs, index) => {
              const method = String(obs.method ?? "?");
              const path = String(obs.path ?? "?");
              const statusCode = Number(obs.status_code ?? 0);
              const durationMs = Number(obs.duration_ms ?? 0);
              return (
              <details key={`${path}-${index}`} style={{ marginBottom: "0.5rem" }}>
                <summary>
                  {method} {path} — {statusCode} ({durationMs} ms)
                </summary>
                <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
                  {JSON.stringify(obs.raw_json ?? obs.parsed_summary, null, 2)}
                </pre>
              </details>
              );
            })}
          </div>
        ) : null}
      </div>
    </details>
  );
}
