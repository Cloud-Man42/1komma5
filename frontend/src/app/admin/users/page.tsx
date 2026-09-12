"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  FilterSelect,
  OverflowMenu,
  PageHeader,
  SearchField,
  StatusBadge,
  SummaryMetricRow,
  TableSkeleton,
  UserAvatar,
  useToast,
} from "@/components/admin-ui";
import { fetchAdminRoles, fetchAdminUsers, updateAdminUser, type UserItem } from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";
import {
  formatDateTime,
  isAdminRole,
  sortUsers,
  userDisplayLabel,
  userStatus,
  type UserSortKey,
} from "@/lib/userAdminUtils";

export default function AdminUsersPage() {
  const { can } = useAuth();
  const router = useRouter();
  const { showToast } = useToast();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [sortKey, setSortKey] = useState<UserSortKey>("name");
  const [sortAsc, setSortAsc] = useState(true);
  const [disableTarget, setDisableTarget] = useState<UserItem | null>(null);
  const [roleOptions, setRoleOptions] = useState<string[]>([]);

  useEffect(() => {
    if (!can("users.read")) {
      setLoading(false);
      return;
    }
    Promise.all([fetchAdminUsers(), can("roles.read") ? fetchAdminRoles() : Promise.resolve([])])
      .then(([userList, roles]) => {
        setUsers(userList);
        setRoleOptions(roles.map((r) => r.name));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can]);

  const summary = useMemo(() => {
    const total = users.length;
    const active = users.filter((u) => userStatus(u) === "active").length;
    const admins = users.filter((u) => u.roles.some((r) => isAdminRole(r.name))).length;
    const locked = users.filter((u) => u.isLocked).length;
    return { total, active, admins, locked };
  }, [users]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = users.filter((user) => {
      if (q) {
        const hay = `${userDisplayLabel(user)} ${user.email} ${user.username}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      const status = userStatus(user);
      if (statusFilter === "active" && status !== "active") return false;
      if (statusFilter === "disabled" && status !== "disabled") return false;
      if (statusFilter === "locked" && status !== "locked") return false;
      if (roleFilter !== "all" && !user.roles.some((r) => r.name === roleFilter)) return false;
      return true;
    });
    list = sortUsers(list, sortKey, sortAsc);
    return list;
  }, [users, search, statusFilter, roleFilter, sortKey, sortAsc]);

  async function toggleActive(user: UserItem) {
    try {
      const updated = await updateAdminUser(user.id, { is_active: !user.isActive });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      showToast(updated.isActive ? "Användare aktiverad" : "Användare inaktiverad", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Kunde inte uppdatera", "error");
    }
  }

  if (!can("users.read")) return <p className="error-text">Saknar behörighet users.read</p>;

  return (
    <div>
      <PageHeader
        title="Användare"
        intro="Hantera konton, roller och site-åtkomst."
        actions={
          can("users.create") ? (
            <Link href="/admin/users/new" className="admin-btn admin-btn-primary">
              + Lägg till användare
            </Link>
          ) : null
        }
      />

      <SummaryMetricRow
        items={[
          { label: "Totalt", value: summary.total },
          { label: "Aktiva", value: summary.active },
          { label: "Admins", value: summary.admins },
          { label: "Låsta", value: summary.locked },
        ]}
      />

      <div className="admin-toolbar">
        <SearchField value={search} onChange={setSearch} placeholder="Sök namn eller e-post…" label="Sök" />
        <FilterSelect
          label="Status"
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: "all", label: "Alla status" },
            { value: "active", label: "Aktiva" },
            { value: "disabled", label: "Inaktiva" },
            { value: "locked", label: "Låsta" },
          ]}
        />
        <FilterSelect
          label="Roll"
          value={roleFilter}
          onChange={setRoleFilter}
          options={[{ value: "all", label: "Alla roller" }, ...roleOptions.map((r) => ({ value: r, label: r }))]}
        />
        <FilterSelect
          label="Sortering"
          value={sortKey}
          onChange={(v) => setSortKey(v as UserSortKey)}
          options={[
            { value: "name", label: "Namn" },
            { value: "lastLogin", label: "Senaste inloggningsförsök" },
            { value: "status", label: "Status" },
          ]}
        />
        <Button variant="ghost" type="button" onClick={() => setSortAsc((v) => !v)}>
          {sortAsc ? "Stigande ↑" : "Fallande ↓"}
        </Button>
      </div>

      {loading ? <TableSkeleton rows={6} /> : null}
      {error ? <p className="error-text">{error}</p> : null}

      {!loading && !error && filtered.length === 0 ? (
        <EmptyState
          title={users.length === 0 ? "Inga användare" : "Inga träffar"}
          text={
            users.length === 0
              ? "Skapa den första användaren för att komma igång."
              : "Justera sökning eller filter."
          }
          action={
            can("users.create") && users.length === 0 ? (
              <Link href="/admin/users/new" className="admin-btn admin-btn-primary">
                Lägg till användare
              </Link>
            ) : undefined
          }
        />
      ) : null}

      {!loading && filtered.length > 0 ? (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Användare</th>
                  <th>Roller</th>
                  <th>Sites</th>
                  <th>Status</th>
                  <th>Senaste inloggningsförsök</th>
                  <th aria-label="Åtgärder" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="admin-user-cell">
                        <UserAvatar name={userDisplayLabel(user)} size="sm" />
                        <div className="admin-user-meta">
                          <span className="admin-user-name">{userDisplayLabel(user)}</span>
                          <span className="admin-user-email">{user.email}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="admin-chip-row">
                        {user.roles.map((r) => (
                          <span key={r.id} className="admin-chip">
                            {r.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div className="admin-chip-row">
                        {user.sites.map((s) => (
                          <span key={s} className="admin-chip">
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={userStatus(user)} />
                    </td>
                    <td>{formatDateTime(user.lastLoginAt)}</td>
                    <td>
                      <OverflowMenu
                        items={[
                          ...(can("users.update")
                            ? [{ label: "Redigera", onClick: () => router.push(`/admin/users/${user.id}`) }]
                            : []),
                          ...(can("users.update")
                            ? [
                                {
                                  label: user.isActive ? "Inaktivera" : "Aktivera",
                                  onClick: () => setDisableTarget(user),
                                },
                              ]
                            : []),
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="admin-mobile-list">
            {filtered.map((user) => (
              <article key={user.id} className="admin-mobile-row">
                <div className="admin-user-cell">
                  <UserAvatar name={userDisplayLabel(user)} size="sm" />
                  <div className="admin-user-meta">
                    <span className="admin-user-name">{userDisplayLabel(user)}</span>
                    <span className="admin-user-email">{user.email}</span>
                  </div>
                </div>
                <p>
                  <StatusBadge status={userStatus(user)} />
                </p>
                <p className="muted">Senaste inloggningsförsök: {formatDateTime(user.lastLoginAt)}</p>
                {can("users.update") ? (
                  <Link href={`/admin/users/${user.id}`} className="admin-btn admin-btn-secondary">
                    Redigera
                  </Link>
                ) : null}
              </article>
            ))}
          </div>
        </>
      ) : null}

      <ConfirmDialog
        open={disableTarget != null}
        title={disableTarget?.isActive ? "Inaktivera användare?" : "Aktivera användare?"}
        message={
          disableTarget
            ? `${userDisplayLabel(disableTarget)} kommer ${disableTarget.isActive ? "inte kunna logga in" : "kunna logga in igen"}.`
            : ""
        }
        confirmLabel={disableTarget?.isActive ? "Inaktivera" : "Aktivera"}
        danger={disableTarget?.isActive ?? false}
        onCancel={() => setDisableTarget(null)}
        onConfirm={() => {
          if (disableTarget) void toggleActive(disableTarget);
          setDisableTarget(null);
        }}
      />
    </div>
  );
}
