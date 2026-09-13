import { authFetch } from "@/lib/auth";

export type TenantSummary = {
  id: number;
  slug: string;
  name: string;
  displayName: string;
  status?: string;
  isActive?: boolean;
  timezone?: string;
  defaultCurrency?: string;
};

export type TenantCreateInput = {
  name: string;
  displayName: string;
  slug: string;
  timezone?: string;
  defaultCurrency?: string;
};

export type TenantUpdateInput = {
  name?: string;
  displayName?: string;
  timezone?: string;
  defaultCurrency?: string;
  isActive?: boolean;
  status?: string;
};

export async function fetchMyTenants(): Promise<TenantSummary[]> {
  const res = await authFetch("/api/tenants/mine");
  if (!res.ok) throw new Error("Failed to load workspaces");
  const body = (await res.json()) as { tenants: TenantSummary[] };
  return body.tenants;
}

export async function selectTenant(tenantId: number): Promise<TenantSummary> {
  const res = await authFetch("/api/tenants/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_id: tenantId }),
  });
  if (!res.ok) throw new Error("Failed to select workspace");
  const body = (await res.json()) as { tenant: TenantSummary };
  return body.tenant;
}

export async function fetchPlatformTenants(): Promise<TenantSummary[]> {
  const res = await authFetch("/api/platform/tenants");
  if (res.status === 403) throw new Error("Platform admin required");
  if (!res.ok) throw new Error("Failed to load platform tenants");
  const body = (await res.json()) as { tenants: TenantSummary[] };
  return body.tenants;
}

export async function createPlatformTenant(input: TenantCreateInput): Promise<TenantSummary> {
  const res = await authFetch("/api/platform/tenants", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: input.name,
      display_name: input.displayName,
      slug: input.slug,
      timezone: input.timezone ?? "Europe/Stockholm",
      default_currency: input.defaultCurrency ?? "SEK",
    }),
  });
  if (res.status === 409) throw new Error("Tenant slug already exists");
  if (res.status === 422) throw new Error("Invalid tenant data");
  if (!res.ok) throw new Error("Failed to create tenant");
  const body = (await res.json()) as { tenant: TenantSummary };
  return body.tenant;
}

export type TenantMember = {
  tenantUserId: number;
  userId: number;
  email: string;
  displayName: string;
  isActive: boolean;
  roles: string[];
};

export async function fetchPlatformTenantMembers(tenantId: number): Promise<TenantMember[]> {
  const res = await authFetch(`/api/platform/tenants/${tenantId}/members`);
  if (res.status === 404) throw new Error("Tenant not found");
  if (!res.ok) throw new Error("Failed to load tenant members");
  const body = (await res.json()) as { members: TenantMember[] };
  return body.members;
}

export async function addPlatformTenantMember(
  tenantId: number,
  email: string,
): Promise<TenantMember> {
  const res = await authFetch(`/api/platform/tenants/${tenantId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 404) throw new Error("Tenant or user not found");
  if (res.status === 409) throw new Error("User already in tenant");
  if (!res.ok) throw new Error("Failed to add tenant member");
  const body = (await res.json()) as { member: TenantMember };
  return body.member;
}

export async function removePlatformTenantMember(tenantId: number, userId: number): Promise<void> {
  const res = await authFetch(`/api/platform/tenants/${tenantId}/members/${userId}`, {
    method: "DELETE",
  });
  if (res.status === 404) throw new Error("Membership not found");
  if (!res.ok) throw new Error("Failed to remove tenant member");
}

export async function deletePlatformTenant(tenantId: number): Promise<void> {
  const res = await authFetch(`/api/platform/tenants/${tenantId}`, { method: "DELETE" });
  if (res.status === 409) throw new Error("Tenant cannot be deleted");
  if (res.status === 404) throw new Error("Tenant not found");
  if (!res.ok) throw new Error("Failed to delete tenant");
}

export async function updatePlatformTenant(
  tenantId: number,
  input: TenantUpdateInput,
): Promise<TenantSummary> {
  const res = await authFetch(`/api/platform/tenants/${tenantId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: input.name,
      display_name: input.displayName,
      timezone: input.timezone,
      default_currency: input.defaultCurrency,
      is_active: input.isActive,
      status: input.status,
    }),
  });
  if (res.status === 404) throw new Error("Tenant not found");
  if (!res.ok) throw new Error("Failed to update tenant");
  const body = (await res.json()) as { tenant: TenantSummary };
  return body.tenant;
}

export function tenantStorageKey(tenantId: number, key: string): string {
  return `tenant:${tenantId}:${key}`;
}

export function clearTenantScopedStorage(tenantId: number | null): void {
  if (typeof window === "undefined" || tenantId === null) return;
  const prefix = `tenant:${tenantId}:`;
  for (const storage of [localStorage, sessionStorage]) {
    const keys = Object.keys(storage).filter((k) => k.startsWith(prefix));
    keys.forEach((k) => storage.removeItem(k));
  }
}
