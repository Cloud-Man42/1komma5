"use client";

import { useCallback, useEffect, useState } from "react";
import { addPublisherKey, fetchPublisherKeys, revokePublisherKey, type PublisherKeyRecord } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";

export function PublishersPanel() {
  const [keys, setKeys] = useState<PublisherKeyRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [publisherId, setPublisherId] = useState("");
  const [keyId, setKeyId] = useState("");
  const [publicKeyHex, setPublicKeyHex] = useState("");

  const load = useCallback(async () => {
    setKeys(await fetchPublisherKeys());
  }, []);

  useEffect(() => {
    if (!getAdminToken()) {
      setError("Admin-token krävs.");
      return;
    }
    void load().catch((err) => setError(err instanceof Error ? err.message : "Kunde inte ladda publishers"));
  }, [load]);

  async function submitKey() {
    setError(null);
    try {
      await addPublisherKey({ publisher_id: publisherId, key_id: keyId, public_key_hex: publicKeyHex });
      setPublisherId("");
      setKeyId("");
      setPublicKeyHex("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte lägga till nyckel");
    }
  }

  async function revoke(publisher: string, key: string) {
    if (!window.confirm(`Revoke publisher key ${publisher}/${key}?`)) return;
    await revokePublisherKey(publisher, key);
    await load();
  }

  return (
    <div className="config-page" data-testid="publishers-panel">
      <ModulesDevicesNav />
      <header className="config-page-header">
        <h1 className="config-page-title">Trusted publishers</h1>
        <p className="config-page-lead">Endast public keys. Private signing keys får aldrig lagras i EMIC.</p>
      </header>
      {error ? <p className="config-error">{error}</p> : null}
      <section className="config-panel">
        <h2 className="config-panel-title">Trusted keys</h2>
        <table className="config-table">
          <thead><tr><th>Publisher</th><th>Key ID</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {keys.map((row) => (
              <tr key={`${row.publisher_id}:${row.key_id}`}>
                <td>{row.publisher_id}</td>
                <td>{row.key_id}</td>
                <td>{row.status}</td>
                <td>
                  {row.status !== "revoked" ? (
                    <button type="button" className="config-button" onClick={() => void revoke(row.publisher_id, row.key_id)}>
                      Revoke
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="config-panel">
        <h2 className="config-panel-title">Add trusted public key</h2>
        <label className="config-field"><span>Publisher ID</span><input value={publisherId} onChange={(e) => setPublisherId(e.target.value)} /></label>
        <label className="config-field"><span>Key ID</span><input value={keyId} onChange={(e) => setKeyId(e.target.value)} /></label>
        <label className="config-field"><span>Public key hex (64 chars)</span><input value={publicKeyHex} onChange={(e) => setPublicKeyHex(e.target.value)} /></label>
        <button type="button" className="config-button" onClick={() => void submitKey()}>Add key</button>
      </section>
    </div>
  );
}
