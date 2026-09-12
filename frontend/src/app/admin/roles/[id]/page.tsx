"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PageHeader, TableSkeleton } from "@/components/admin-ui";
import { RoleEditorForm } from "@/components/admin/RoleEditorForm";
import {
  fetchAdminPermissions,
  fetchAdminRoles,
  type PermissionItem,
  type RoleItem,
} from "@/lib/adminUsersApi";
import { useAuth } from "@/lib/authContext";

export default function AdminRoleEditPage() {
  const { can } = useAuth();
  const params = useParams();
  const roleId = Number(params.id);
  const [role, setRole] = useState<RoleItem | null>(null);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!can("roles.read") || Number.isNaN(roleId)) {
      setLoading(false);
      return;
    }
    Promise.all([fetchAdminRoles(), fetchAdminPermissions()])
      .then(([roles, perms]) => {
        const found = roles.find((r) => r.id === roleId) ?? null;
        if (!found) throw new Error("Rollen hittades inte");
        setRole(found);
        setPermissions(perms);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Fel"))
      .finally(() => setLoading(false));
  }, [can, roleId]);

  if (!can("roles.read")) return <p className="error-text">Saknar behörighet roles.read</p>;
  if (loading) return <TableSkeleton rows={4} />;
  if (error || !role) return <p className="error-text">{error ?? "Rollen hittades inte"}</p>;

  const readOnly = role.isSystemRole || role.name === "SUPER_ADMIN" || !can("roles.manage");

  return (
    <div>
      <PageHeader
        title={role.name}
        intro={readOnly ? "Systemroll med full behörighet." : "Redigera beskrivning och behörigheter."}
      />
      <RoleEditorForm
        mode="edit"
        role={role}
        permissions={permissions}
        readOnly={readOnly}
        onSaved={setRole}
      />
    </div>
  );
}
