/** Admin API client for EMIC user/role/audit management. */

import { authFetch } from "@/lib/auth";

export interface UserRoleRef {
  id: number;
  name: string;
}

export interface UserItem {
  id: number;
  username: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  displayName: string | null;
  isActive: boolean;
  isLocked: boolean;
  mustChangePassword: boolean;
  lastLoginAt: string | null;
  roles: UserRoleRef[];
  sites: string[];
}

export interface RolePermissionRef {
  id: number;
  key: string;
  name?: string;
}

export interface RoleItem {
  id: number;
  name: string;
  description: string | null;
  isSystemRole: boolean;
  permissions: RolePermissionRef[];
}

export interface PermissionItem {
  id: number;
  key: string;
  name: string;
  description: string;
  group: string;
}

export interface AuditEvent {
  id: number;
  recordedAt: string;
  userId: number | null;
  username: string | null;
  eventType: string;
  entityType: string | null;
  entityId: string | null;
  siteId: number | null;
  action: string;
  success: boolean;
  sourceIp: string | null;
}

export interface SiteOption {
  id: number;
  slug: string;
  name: string;
}

export interface UserCreatePayload {
  username: string;
  email: string;
  password: string;
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  role_ids?: number[];
  site_ids?: number[];
  must_change_password?: boolean;
}

export interface UserUpdatePayload {
  username?: string;
  email?: string;
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  is_active?: boolean;
  role_ids?: number[];
  site_ids?: number[];
}

export interface RoleCreatePayload {
  name: string;
  description?: string | null;
  permission_ids?: number[];
}

export interface RoleUpdatePayload {
  description?: string | null;
  permission_ids?: number[];
}

export interface AuditQuery {
  limit?: number;
  user_id?: number;
  event_type?: string;
  site_id?: number;
  success?: boolean;
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string | { msg?: string }[] };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // ignore
  }
  return `Begäran misslyckades (${res.status})`;
}

export async function fetchAdminUsers(): Promise<UserItem[]> {
  const res = await authFetch("/api/admin/users");
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { users: UserItem[] };
  return body.users;
}

export async function createAdminUser(payload: UserCreatePayload): Promise<UserItem> {
  const res = await authFetch("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<UserItem>;
}

export async function updateAdminUser(userId: number, payload: UserUpdatePayload): Promise<UserItem> {
  const res = await authFetch(`/api/admin/users/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<UserItem>;
}

export async function resetAdminUserPassword(
  userId: number,
  newPassword: string,
  mustChangePassword = true,
): Promise<void> {
  const res = await authFetch(`/api/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword, must_change_password: mustChangePassword }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function fetchAdminRoles(): Promise<RoleItem[]> {
  const res = await authFetch("/api/admin/roles");
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { roles: RoleItem[] };
  return body.roles;
}

export async function fetchAdminPermissions(): Promise<PermissionItem[]> {
  const res = await authFetch("/api/admin/roles/permissions");
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { permissions: PermissionItem[] };
  return body.permissions;
}

export async function createAdminRole(payload: RoleCreatePayload): Promise<RoleItem> {
  const res = await authFetch("/api/admin/roles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<RoleItem>;
}

export async function updateAdminRole(roleId: number, payload: RoleUpdatePayload): Promise<RoleItem> {
  const res = await authFetch(`/api/admin/roles/${roleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<RoleItem>;
}

export async function deleteAdminRole(roleId: number): Promise<void> {
  const res = await authFetch(`/api/admin/roles/${roleId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function fetchAuthAudit(query: AuditQuery = {}): Promise<AuditEvent[]> {
  const params = new URLSearchParams();
  if (query.limit != null) params.set("limit", String(query.limit));
  if (query.user_id != null) params.set("user_id", String(query.user_id));
  if (query.event_type) params.set("event_type", query.event_type);
  if (query.site_id != null) params.set("site_id", String(query.site_id));
  if (query.success != null) params.set("success", String(query.success));
  const qs = params.toString();
  const res = await authFetch(`/api/admin/auth-audit${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { events: AuditEvent[] };
  return body.events;
}

/** Site options for admin forms — includes numeric ids required by user API. */
export async function fetchAdminSiteOptions(): Promise<SiteOption[]> {
  const res = await authFetch("/api/admin/users/site-options");
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { sites: SiteOption[] };
  return body.sites;
}
