"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchInstallationPolicy, updateInstallationPolicy, type InstallationPolicy } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";

const TIER_OPTIONS = ["OFFICIAL", "VERIFIED", "ORG_APPROVED", "COMMUNITY"];

export function OrganizationPolicyPanel() {
  const [policy, setPolicy] = useState<InstallationPolicy | null>(null);
  const [allowedTiers, setAllowedTiers] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);

  const load = useCallback(async () => {
    const row = await fetchInstallationPolicy();
    setPolicy(row);
    setAllowedTiers(row.allowed_tiers);
    setConflict(false);
  }, []);

  useEffect(() => {
    if (!getAdminToken()) {
      setError("Admin-token krävs.");
      return;
    }
    void load().catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda policy"));
  }, [load]);

  function toggleTier(tier: string) {
    setAllowedTiers((prev) => (prev.includes(tier) ? prev.filter((t) => t !== tier) : [...prev, tier]));
  }

  async function save() {
    if (!policy) return;
    setError(null);
    setConflict(false);
    try {
      const updated = await updateInstallationPolicy({
        expected_version: policy.policy_version,
        allowed_tiers: allowedTiers,
      });
      setPolicy(updated);
      setAllowedTiers(updated.allowed_tiers);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kunde inte spara policy";
      if (message.toLowerCase().includes("conflict") || message.includes("409")) {
        setConflict(true);
      }
      setError(message);
    }
  }

  return (
    <div className="config-page" data-testid="organization-policy-panel">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <h1 className="config-page-title">Organization installation policy</h1>
        <p className="config-page-lead">Version {policy?.policy_version ?? "—"} — optimistic concurrency via expected_version.</p>
      </header>
      {error ? <p className="config-error">{error}</p> : null}
      {conflict ? <p className="config-error">Policy conflict — reload and retry with current version.</p> : null}
      <section className="config-panel">
        <h2 className="config-panel-title">Allowed tiers</h2>
        <ul>
          {TIER_OPTIONS.map((tier) => (
            <li key={tier}>
              <label>
                <input
                  type="checkbox"
                  checked={allowedTiers.includes(tier)}
                  onChange={() => toggleTier(tier)}
                />
                {tier}
              </label>
            </li>
          ))}
        </ul>
        <button type="button" className="config-button" onClick={() => void save()} disabled={!policy}>
          Save policy
        </button>
      </section>
    </div>
  );
}
