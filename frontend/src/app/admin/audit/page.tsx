"use client";

import { useEffect, useMemo, useState } from "react";
import {
  EmptyState,
  FilterSelect,
  PageHeader,
  SearchField,
  TableSkeleton,
} from "@/components/admin-ui";
import { fetchAdminUsers, fetchAuthAudit, type AuditEvent, type UserItem } from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";
import { formatDateTime } from "@/lib/userAdminUtils";

export default function AdminAuthAuditPage() {
  const { can } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventType, setEventType] = useState("all");
  const [userId, setUserId] = useState("all");
  const [successFilter, setSuccessFilter] = useState("all");
  const [limit, setLimit] = useState("100");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!can("audit.read")) {
      setLoading(false);
      return;
    }
    if (can("users.read")) {
      fetchAdminUsers().then(setUsers).catch(() => undefined);
    }
  }, [can]);

  useEffect(() => {
    if (!can("audit.read")) return;
    setLoading(true);
    fetchAuthAudit({
      limit: Number(limit) || 100,
      user_id: userId === "all" ? undefined : Number(userId),
      event_type: eventType === "all" ? undefined : eventType,
      success: successFilter === "all" ? undefined : successFilter === "ok",
    })
      .then(setEvents)
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can, eventType, userId, successFilter, limit]);

  const eventTypes = useMemo(() => {
    const set = new Set(events.map((e) => e.eventType));
    return [...set].sort();
  }, [events]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return events;
    return events.filter((e) =>
      `${e.username ?? ""} ${e.eventType} ${e.action} ${e.entityType ?? ""} ${e.entityId ?? ""}`
        .toLowerCase()
        .includes(q),
    );
  }, [events, search]);

  function toggleExpanded(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (!can("audit.read")) return <p className="error-text">Saknar behörighet audit.read</p>;

  return (
    <div>
      <PageHeader title="Auth audit" intro="Inloggning, lösenord och administrativa händelser." />

      <div className="admin-toolbar">
        <SearchField value={search} onChange={setSearch} placeholder="Sök i resultat…" label="Sök" />
        <FilterSelect
          label="Händelsetyp"
          value={eventType}
          onChange={setEventType}
          options={[{ value: "all", label: "Alla typer" }, ...eventTypes.map((t) => ({ value: t, label: t }))]}
        />
        <FilterSelect
          label="Användare"
          value={userId}
          onChange={setUserId}
          options={[
            { value: "all", label: "Alla användare" },
            ...users.map((u) => ({ value: String(u.id), label: u.displayName ?? u.username })),
          ]}
        />
        <FilterSelect
          label="Resultat"
          value={successFilter}
          onChange={setSuccessFilter}
          options={[
            { value: "all", label: "Alla" },
            { value: "ok", label: "Lyckade" },
            { value: "fail", label: "Misslyckade" },
          ]}
        />
        <FilterSelect
          label="Antal"
          value={limit}
          onChange={setLimit}
          options={[
            { value: "50", label: "50" },
            { value: "100", label: "100" },
            { value: "250", label: "250" },
          ]}
        />
      </div>

      {loading ? <TableSkeleton rows={6} /> : null}
      {error ? <p className="error-text">{error}</p> : null}

      {!loading && !error && filtered.length === 0 ? (
        <EmptyState title="Inga händelser" text="Justera filter eller vänta på nya loggposter." />
      ) : null}

      {!loading && filtered.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Tid</th>
                <th>Användare</th>
                <th>Händelse</th>
                <th>Action</th>
                <th>Resultat</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.flatMap((row) => {
                const rows = [
                  <tr key={row.id}>
                    <td>{formatDateTime(row.recordedAt)}</td>
                    <td>{row.username ?? "—"}</td>
                    <td>{row.eventType}</td>
                    <td>{row.action}</td>
                    <td>{row.success ? "OK" : "Fel"}</td>
                    <td>
                      <button type="button" className="admin-btn admin-btn-ghost" onClick={() => toggleExpanded(row.id)}>
                        {expanded.has(row.id) ? "Dölj" : "Detaljer"}
                      </button>
                    </td>
                  </tr>,
                ];
                if (expanded.has(row.id)) {
                  rows.push(
                    <tr key={`${row.id}-detail`}>
                      <td colSpan={6} className="admin-audit-expand">
                        IP: {row.sourceIp ?? "—"} · Entitet: {row.entityType ?? "—"} / {row.entityId ?? "—"} · Site:{" "}
                        {row.siteId ?? "—"}
                      </td>
                    </tr>,
                  );
                }
                return rows;
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
