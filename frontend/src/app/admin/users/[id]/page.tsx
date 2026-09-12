"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { PageHeader, TableSkeleton } from "@/components/admin-ui";
import { UserEditorForm } from "@/components/admin/UserEditorForm";
import {
  fetchAdminRoles,
  fetchAdminSiteOptions,
  fetchAdminUsers,
  type RoleItem,
  type SiteOption,
  type UserItem,
} from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";
import { userDisplayLabel } from "@/lib/userAdminUtils";

export default function AdminUserEditPage() {
  const { can } = useAuth();
  const params = useParams();
  const userId = Number(params.id);
  const [user, setUser] = useState<UserItem | null>(null);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [sites, setSites] = useState<SiteOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const siteSlugToId = useMemo(() => new Map(sites.map((s) => [s.slug, s.id])), [sites]);

  useEffect(() => {
    if (!can("users.update") || Number.isNaN(userId)) {
      setLoading(false);
      return;
    }
    Promise.all([fetchAdminUsers(), fetchAdminRoles(), fetchAdminSiteOptions()])
      .then(([users, roleList, siteList]) => {
        const found = users.find((u) => u.id === userId) ?? null;
        if (!found) throw new Error("Användaren hittades inte");
        setUser(found);
        setRoles(roleList);
        setSites(siteList);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can, userId]);

  if (!can("users.update")) return <p className="error-text">Saknar behörighet users.update</p>;
  if (loading) return <TableSkeleton rows={4} />;
  if (error || !user) return <p className="error-text">{error ?? "Användaren hittades inte"}</p>;

  return (
    <div>
      <PageHeader title={userDisplayLabel(user)} intro="Redigera profil, åtkomst och säkerhet." />
      <UserEditorForm
        mode="edit"
        user={user}
        roles={roles}
        sites={sites}
        siteSlugToId={siteSlugToId}
        onSaved={setUser}
      />
    </div>
  );
}
