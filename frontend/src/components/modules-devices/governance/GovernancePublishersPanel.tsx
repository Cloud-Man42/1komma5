"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createGovernancePublisher,
  fetchGovernancePublishers,
  fetchPublisherKeys,
  suspendGovernancePublisher,
  verifyGovernancePublisher,
  type GovernancePublisher,
  type PublisherKeyRecord,
} from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";

export function GovernancePublishersPanel() {
  const [publishers, setPublishers] = useState<GovernancePublisher[]>([]);
  const [keys, setKeys] = useState<PublisherKeyRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [publisherId, setPublisherId] = useState("");
  const [displayName, setDisplayName] = useState("");

  const load = useCallback(async () => {
    const [pubs, keyRows] = await Promise.all([fetchGovernancePublishers(), fetchPublisherKeys()]);
    setPublishers(pubs);
    setKeys(keyRows);
  }, []);

  useEffect(() => {
    if (!getAdminToken()) {
      setError("Admin-token krävs.");
      return;
    }
    void load().catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda governance"));
  }, [load]);

  async function createPublisher() {
    setError(null);
    try {
      await createGovernancePublisher({ publisher_id: publisherId, display_name: displayName });
      setPublisherId("");
      setDisplayName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte skapa publisher");
    }
  }

  async function verify(id: string) {
    await verifyGovernancePublisher(id);
    await load();
  }

  async function suspend(id: string) {
    if (!window.confirm(`Suspend publisher ${id}?`)) return;
    await suspendGovernancePublisher(id);
    await load();
  }

  const keyCount = (id: string) => keys.filter((k) => k.publisher_id === id).length;

  return (
    <div className="config-page" data-testid="governance-publishers-panel">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <h1 className="config-page-title">Publisher governance</h1>
        <p className="config-page-lead">Tier, lifecycle och trusted keys per publisher.</p>
      </header>
      {error ? <p className="config-error">{error}</p> : null}
      <section className="config-panel">
        <h2 className="config-panel-title">Publishers</h2>
        <table className="config-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Tier</th>
              <th>Status</th>
              <th>Modules</th>
              <th>Keys</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {publishers.map((row) => (
              <tr key={row.publisher_id}>
                <td>{row.publisher_id}</td>
                <td>{row.display_name}</td>
                <td>{row.tier}</td>
                <td>{row.status}</td>
                <td>{row.module_count}</td>
                <td>{keyCount(row.publisher_id)}</td>
                <td>
                  {row.status === "PENDING_VERIFICATION" ? (
                    <button type="button" className="config-button" onClick={() => void verify(row.publisher_id)}>
                      Verify
                    </button>
                  ) : null}
                  {row.status === "ACTIVE" ? (
                    <button type="button" className="config-button" onClick={() => void suspend(row.publisher_id)}>
                      Suspend
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="config-panel">
        <h2 className="config-panel-title">Create publisher</h2>
        <label className="config-field">
          <span>Publisher ID</span>
          <input value={publisherId} onChange={(e) => setPublisherId(e.target.value)} />
        </label>
        <label className="config-field">
          <span>Display name</span>
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </label>
        <button type="button" className="config-button" onClick={() => void createPublisher()}>
          Create
        </button>
      </section>
    </div>
  );
}
