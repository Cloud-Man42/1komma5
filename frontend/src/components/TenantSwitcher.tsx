"use client";

import { useTenantSelection } from "@/lib/TenantSelectionProvider";

export function TenantSwitcher() {
  const { tenants, currentTenant, loading, switchTenant } = useTenantSelection();
  if (loading || tenants.length <= 1) return null;

  return (
    <label className="tenant-switcher">
      <span className="sr-only">Workspace</span>
      <select
        className="admin-input tenant-switcher-select"
        value={currentTenant?.id ?? ""}
        onChange={(event) => {
          const tenantId = Number(event.target.value);
          if (tenantId > 0) void switchTenant(tenantId);
        }}
      >
        {tenants.map((tenant) => (
          <option key={tenant.id} value={tenant.id}>
            {tenant.displayName || tenant.name}
          </option>
        ))}
      </select>
    </label>
  );
}
