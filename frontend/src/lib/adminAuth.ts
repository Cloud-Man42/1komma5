const STORAGE_KEY = "emic_admin_token";

export function getAdminToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(STORAGE_KEY)?.trim() ?? "";
}

export function setAdminToken(token: string): void {
  if (typeof window === "undefined") return;
  const trimmed = token.trim();
  if (trimmed) {
    sessionStorage.setItem(STORAGE_KEY, trimmed);
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

export function adminAuthHeaders(extra?: HeadersInit): HeadersInit {
  const token = getAdminToken();
  if (!token) return extra ?? {};
  return {
    ...(extra ?? {}),
    Authorization: `Bearer ${token}`,
  };
}

export async function adminFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: adminAuthHeaders(init?.headers),
  });
}
