"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader, TableSkeleton } from "@/components/admin-ui";
import { UserEditorForm } from "@/components/admin/UserEditorForm";
import { fetchAdminRoles, fetchAdminSiteOptions } from "@/lib/adminUsersApi";
import type { RoleItem, SiteOption } from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";

export default function AdminUserCreatePage() {
  const { can } = useAuth();
  const router = useRouter();
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [sites, setSites] = useState<SiteOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const siteSlugToId = useMemo(() => new Map(sites.map((s) => [s.slug, s.id])), [sites]);

  useEffect(() => {
    if (!can("users.create")) {
      setLoading(false);
      return;
    }
    Promise.all([fetchAdminRoles(), fetchAdminSiteOptions()])
      .then(([roleList, siteList]) => {
        setRoles(roleList);
        setSites(siteList);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can]);

  if (!can("users.create")) return <p className="error-text">Saknar behörighet users.create</p>;
  if (loading) return <TableSkeleton rows={4} />;
  if (error) return <p className="error-text">{error}</p>;

  return (
    <div>
      <PageHeader title="Ny användare" intro="Skapa konto med roller och site-åtkomst." />
      <UserEditorForm
        mode="create"
        roles={roles}
        sites={sites}
        siteSlugToId={siteSlugToId}
        onSaved={(user) => router.push(`/admin/users/${user.id}`)}
      />
    </div>
  );
}
