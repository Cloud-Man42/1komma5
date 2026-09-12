const STORAGE_KEY = "emic_admin_token";
const LEGACY_STORAGE_KEY = "emic_admin_token";

export function getAdminToken(): string {
  if (typeof window === "undefined") return "";
  const fromLocal = localStorage.getItem(STORAGE_KEY)?.trim();
  if (fromLocal) return fromLocal;

  const legacy = sessionStorage.getItem(LEGACY_STORAGE_KEY)?.trim();
  if (legacy) {
    localStorage.setItem(STORAGE_KEY, legacy);
    sessionStorage.removeItem(LEGACY_STORAGE_KEY);
    return legacy;
  }
  return "";
}

export function setAdminToken(token: string): void {
  if (typeof window === "undefined") return;
  const trimmed = token.trim();
  sessionStorage.removeItem(LEGACY_STORAGE_KEY);
  if (trimmed) {
    localStorage.setItem(STORAGE_KEY, trimmed);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

/** One-shot LAN setup: ?emic_setup_token=... saves token and strips the query param. */
export function applySetupTokenFromUrl(): boolean {
  if (typeof window === "undefined") return false;

  const params = new URLSearchParams(window.location.search);
  const setupToken = params.get("emic_setup_token")?.trim();
  if (!setupToken) return false;

  setAdminToken(setupToken);
  params.delete("emic_setup_token");
  const query = params.toString();
  const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
  window.history.replaceState({}, "", nextUrl);
  return true;
}

export function adminAuthHeaders(extra?: HeadersInit): HeadersInit {
  const token = getAdminToken();
  if (!token) return extra ?? {};
  return {
    ...(extra ?? {}),
    Authorization: `Bearer ${token}`,
  };
}

export class AdminAuthRequiredError extends Error {
  constructor(message = "Admin token required") {
    super(message);
    this.name = "AdminAuthRequiredError";
  }
}

function dispatchAdminAuthEvent(status: 401 | 403): void {
  if (typeof window === "undefined") return;
  const eventName = status === 403 ? "emic:admin-auth-invalid" : "emic:admin-auth-required";
  window.dispatchEvent(new CustomEvent(eventName));
}

export async function adminFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(adminAuthHeaders(init?.headers));
  if (typeof document !== "undefined") {
    const csrfMatch = document.cookie.match(/(?:^|; )emic_csrf=([^;]*)/);
    const csrf = csrfMatch ? decodeURIComponent(csrfMatch[1]) : "";
    if (csrf && !["GET", "HEAD", "OPTIONS"].includes(method)) {
      headers.set("X-CSRF-Token", csrf);
    }
  }
  const response = await fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401 || response.status === 403) {
    dispatchAdminAuthEvent(response.status as 401 | 403);
  }
  return response;
}
