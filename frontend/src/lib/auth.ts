/** EMIC session auth (cookie-based) with optional break-glass Bearer token. */

import { adminAuthHeaders, getAdminToken } from "@/lib/adminAuth";

export const CSRF_HEADER = "X-CSRF-Token";
export const CSRF_COOKIE = "emic_csrf";

export interface AuthUser {
  id: number | null;
  username: string;
  email: string;
  displayName: string;
  roles: string[];
  permissions: string[];
  sites: string[];
  mustChangePassword: boolean;
  authMethod: string;
}

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

export function getCsrfToken(): string {
  return readCookie(CSRF_COOKIE);
}

export function hasPermission(user: AuthUser | null, permission: string): boolean {
  if (!user) return false;
  if (user.roles.includes("SUPER_ADMIN")) return true;
  if (user.permissions.includes("*")) return true;
  return user.permissions.includes(permission);
}

export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(adminAuthHeaders(init?.headers));
  const csrf = getCsrfToken();
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set(CSRF_HEADER, csrf);
  }
  const response = await fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });
  if (typeof window !== "undefined") {
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent("emic:auth-required"));
    } else if (response.status === 403) {
      window.dispatchEvent(new CustomEvent("emic:auth-forbidden"));
    }
  }
  return response;
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const response = await authFetch("/api/auth/me");
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Auth me failed: ${response.status}`);
  return (await response.json()) as AuthUser;
}

export async function login(usernameOrEmail: string, password: string): Promise<AuthUser> {
  const response = await authFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? "Inloggning misslyckades");
  }
  return (await response.json()) as AuthUser;
}

export async function logout(): Promise<void> {
  await authFetch("/api/auth/logout", { method: "POST" });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await authFetch("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? "Kunde inte byta lösenord");
  }
}

/** True when break-glass admin token is configured client-side. */
export function hasBreakGlassToken(): boolean {
  return Boolean(getAdminToken());
}
