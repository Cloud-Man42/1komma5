"use client";

import { useState } from "react";
import { evaluateModulePolicy, type PolicyEvaluation } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";

export function PolicyDiagnosticsPanel() {
  const [moduleId, setModuleId] = useState("");
  const [publisherId, setPublisherId] = useState("");
  const [permissions, setPermissions] = useState("");
  const [result, setResult] = useState<PolicyEvaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runEvaluation() {
    if (!getAdminToken()) {
      setError("Admin-token krävs.");
      return;
    }
    setError(null);
    try {
      const evaluation = await evaluateModulePolicy({
        module_id: moduleId,
        publisher_id: publisherId,
        permissions: permissions
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean),
      });
      setResult(evaluation);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Evaluation failed");
    }
  }

  return (
    <div className="config-page" data-testid="policy-diagnostics-panel">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <h1 className="config-page-title">Policy diagnostics</h1>
        <p className="config-page-lead">Dry-run evaluate — displays API decision only (no install side effects).</p>
      </header>
      {error ? <p className="config-error">{error}</p> : null}
      <section className="config-panel">
        <label className="config-field">
          <span>Module ID</span>
          <input value={moduleId} onChange={(e) => setModuleId(e.target.value)} />
        </label>
        <label className="config-field">
          <span>Publisher ID</span>
          <input value={publisherId} onChange={(e) => setPublisherId(e.target.value)} />
        </label>
        <label className="config-field">
          <span>Permissions (comma-separated)</span>
          <input value={permissions} onChange={(e) => setPermissions(e.target.value)} />
        </label>
        <button type="button" className="config-button" onClick={() => void runEvaluation()}>
          Evaluate
        </button>
      </section>
      {result ? (
        <section className="config-panel" data-testid="policy-evaluation-result">
          <h2 className="config-panel-title">Result: {result.decision}</h2>
          <p>{result.explanation}</p>
          <p>Tier: {result.publisher_tier ?? "—"}</p>
          <p>Control capable: {result.control_capable ? "yes" : "no"}</p>
          <ul>
            {result.reason_codes.map((code) => (
              <li key={code}>{code}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
