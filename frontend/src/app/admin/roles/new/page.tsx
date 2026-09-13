"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader, TableSkeleton } from "@/components/admin-ui";
import { RoleEditorForm } from "@/components/admin/RoleEditorForm";
import { fetchAdminPermissions, type PermissionItem } from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";

export default function AdminRoleCreatePage() {
  const { can } = useAuth();
  const router = useRouter();
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!can("roles.manage")) {
      setLoading(false);
      return;
    }
    fetchAdminPermissions()
      .then(setPermissions)
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can]);

  if (!can("roles.manage")) return <p className="error-text">Saknar behörighet roles.manage</p>;
  if (loading) return <TableSkeleton rows={4} />;
  if (error) return <p className="error-text">{error}</p>;

  return (
    <div>
      <PageHeader title="Ny roll" intro="Definiera behörigheter för en anpassad roll." />
      <RoleEditorForm
        mode="create"
        permissions={permissions}
        onSaved={(role) => router.push(`/admin/roles/${role.id}`)}
      />
    </div>
  );
}
