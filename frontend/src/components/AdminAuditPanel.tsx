"use client";

import { useEffect, useState } from "react";
import type { AdminAuditEntry } from "@/lib/api";
import { fetchAdminAuditLog } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("sv-SE");
}

function formatSummary(summary: Record<string, unknown> | null): string {
  if (!summary || Object.keys(summary).length === 0) return "—";
  return JSON.stringify(summary);
}

export function AdminAuditPanel() {
  const [entries, setEntries] = useState<AdminAuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const hasToken = typeof window !== "undefined" && Boolean(getAdminToken());

  useEffect(() => {
    if (!hasToken) {
      setLoading(false);
      setEntries([]);
      return;
    }

    let active = true;
    setLoading(true);
    fetchAdminAuditLog(50)
      .then((payload) => {
        if (!active) return;
        setEntries(payload.entries);
        setError(null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setEntries([]);
        setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [hasToken]);

  return (
    <section className="card config-card" data-testid="admin-audit-panel">
      <header>
        <h3 className="config-section-title">Admin audit-logg</h3>
        <p className="muted config-env-intro">
          Senaste admin-ändringar (sites, spa, laddboxar, fordon, enheter).
        </p>
      </header>

      {!hasToken ? (
        <p className="muted">Ange admin-token ovan för att visa audit-loggen.</p>
      ) : null}

      {hasToken && loading ? <p className="muted">Hämtar audit-logg…</p> : null}

      {hasToken && error ? <p className="form-error">{error}</p> : null}

      {hasToken && !loading && !error && entries.length === 0 ? (
        <p className="muted">Inga audit-händelser ännu.</p>
      ) : null}

      {hasToken && entries.length > 0 ? (
        <div className="admin-audit-table-wrap">
          <table className="admin-audit-table">
            <thead>
              <tr>
                <th>Tid</th>
                <th>Action</th>
                <th>Site</th>
                <th>Resurs</th>
                <th>Sammanfattning</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} data-testid={`admin-audit-row-${entry.id}`}>
                  <td>{formatTimestamp(entry.recorded_at)}</td>
                  <td>
                    <code>{entry.action}</code>
                  </td>
                  <td>{entry.site_slug ?? "—"}</td>
                  <td>
                    {entry.resource_type ?? "—"}
                    {entry.resource_id ? ` #${entry.resource_id}` : ""}
                  </td>
                  <td className="admin-audit-summary">{formatSummary(entry.summary)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
