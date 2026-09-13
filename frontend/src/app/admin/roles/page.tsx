"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  PageHeader,
  TableSkeleton,
  useToast,
} from "@/components/admin-ui";
import {
  createAdminRole,
  deleteAdminRole,
  fetchAdminRoles,
  fetchAdminUsers,
  type RoleItem,
} from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";

export default function AdminRolesPage() {
  const { can } = useAuth();
  const router = useRouter();
  const { showToast } = useToast();
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [userCounts, setUserCounts] = useState<Map<number, number>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RoleItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!can("roles.read")) {
      setLoading(false);
      return;
    }
    Promise.all([fetchAdminRoles(), can("users.read") ? fetchAdminUsers() : Promise.resolve([])])
      .then(([roleList, users]) => {
        setRoles(roleList);
        const counts = new Map<number, number>();
        for (const user of users) {
          for (const role of user.roles) {
            counts.set(role.id, (counts.get(role.id) ?? 0) + 1);
          }
        }
        setUserCounts(counts);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can]);

  const sortedRoles = useMemo(
    () => [...roles].sort((a, b) => a.name.localeCompare(b.name, "sv")),
    [roles],
  );

  async function duplicateRole(role: RoleItem) {
    if (!can("roles.manage")) return;
    try {
      const copy = await createAdminRole({
        name: `${role.name}_kopia`,
        description: role.description,
        permission_ids: role.permissions.map((p) => p.id),
      });
      showToast("Roll duplicerad", "success");
      router.push(`/admin/roles/${copy.id}`);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Kunde inte duplicera", "error");
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteAdminRole(deleteTarget.id);
      setRoles((prev) => prev.filter((r) => r.id !== deleteTarget.id));
      showToast("Roll borttagen", "success");
      setDeleteTarget(null);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Kunde inte ta bort roll", "error");
    } finally {
      setDeleting(false);
    }
  }

  if (!can("roles.read")) return <p className="error-text">Saknar behörighet roles.read</p>;

  return (
    <div>
      <PageHeader
        title="Roller"
        intro="Behörighetsmallar för EMIC-användare."
        actions={
          can("roles.manage") ? (
            <Link href="/admin/roles/new" className="admin-btn admin-btn-primary">
              + Ny roll
            </Link>
          ) : null
        }
      />

      {loading ? <TableSkeleton rows={4} /> : null}
      {error ? <p className="error-text">{error}</p> : null}

      {!loading && !error && sortedRoles.length === 0 ? (
        <EmptyState title="Inga roller" text="Skapa en anpassad roll för finare åtkomstkontroll." />
      ) : null}

      {!loading && sortedRoles.length > 0 ? (
        <div className="admin-role-list">
          {sortedRoles.map((role) => (
            <article key={role.id} className="admin-role-list-card">
              <h3>
                {role.name}
                {role.isSystemRole ? <span className="admin-chip">System</span> : null}
              </h3>
              <p className="muted">{role.description || "Ingen beskrivning"}</p>
              <div className="admin-role-meta">
                <span className="admin-chip">{userCounts.get(role.id) ?? 0} användare</span>
                <span className="admin-chip">{role.permissions.length} behörigheter</span>
              </div>
              <div className="admin-role-actions">
                <Link href={`/admin/roles/${role.id}`} className="admin-btn admin-btn-secondary">
                  {role.name === "SUPER_ADMIN" ? "Visa" : "Redigera"}
                </Link>
                {can("roles.manage") && !role.isSystemRole ? (
                  <>
                    <Button variant="ghost" type="button" onClick={() => void duplicateRole(role)}>
                      Duplicera
                    </Button>
                    <Button variant="danger" type="button" onClick={() => setDeleteTarget(role)}>
                      Ta bort
                    </Button>
                  </>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      <ConfirmDialog
        open={deleteTarget != null}
        title="Ta bort roll?"
        message={deleteTarget ? `Rollen ${deleteTarget.name} tas bort permanent.` : ""}
        confirmLabel="Ta bort"
        danger
        loading={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  );
}
