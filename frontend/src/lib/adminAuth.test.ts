import { describe, expect, it, beforeEach, vi } from "vitest";

import {
  adminAuthHeaders,
  adminFetch,
  applySetupTokenFromUrl,
  getAdminToken,
  setAdminToken,
} from "@/lib/adminAuth";

describe("adminAuth", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("returns empty token by default", () => {
    expect(getAdminToken()).toBe("");
    expect(adminAuthHeaders()).toEqual({});
  });

  it("stores token in localStorage", () => {
    setAdminToken("secret-token");
    expect(getAdminToken()).toBe("secret-token");
    expect(localStorage.getItem("emic_admin_token")).toBe("secret-token");
    expect(adminAuthHeaders()).toEqual({ Authorization: "Bearer secret-token" });
  });

  it("migrates legacy sessionStorage token to localStorage", () => {
    sessionStorage.setItem("emic_admin_token", "legacy-token");
    expect(getAdminToken()).toBe("legacy-token");
    expect(localStorage.getItem("emic_admin_token")).toBe("legacy-token");
    expect(sessionStorage.getItem("emic_admin_token")).toBeNull();
  });

  it("clears token when empty string is saved", () => {
    setAdminToken("secret-token");
    setAdminToken("");
    expect(getAdminToken()).toBe("");
  });

  it("adminFetch attaches bearer token to requests", async () => {
    setAdminToken("secret-token");
    const fetchMock = vi.fn().mockResolvedValue({ status: 200, ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await adminFetch("/api/sites");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sites",
      expect.objectContaining({ credentials: "include", headers: expect.any(Headers) }),
    );
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer secret-token");

    vi.unstubAllGlobals();
  });

  it("adminFetch dispatches auth-required event on 401", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 401, ok: false });
    vi.stubGlobal("fetch", fetchMock);
    const events: string[] = [];
    window.addEventListener("emic:admin-auth-required", () => events.push("required"));

    await adminFetch("/api/sites");
    expect(events).toEqual(["required"]);

    vi.unstubAllGlobals();
  });

  it("applySetupTokenFromUrl stores token and strips query param", () => {
    window.history.replaceState({}, "", "/?emic_setup_token=from-url&foo=bar");

    expect(applySetupTokenFromUrl()).toBe(true);
    expect(getAdminToken()).toBe("from-url");
    expect(window.location.pathname).toBe("/");
    expect(window.location.search).toBe("?foo=bar");
  });

  it("applySetupTokenFromUrl returns false when param missing", () => {
    window.history.replaceState({}, "", "/dashboard");
    expect(applySetupTokenFromUrl()).toBe(false);
  });

  it("adminFetch dispatches auth-invalid event on 403", async () => {
    setAdminToken("wrong-token");
    const fetchMock = vi.fn().mockResolvedValue({ status: 403, ok: false });
    vi.stubGlobal("fetch", fetchMock);
    const events: string[] = [];
    window.addEventListener("emic:admin-auth-invalid", () => events.push("invalid"));

    await adminFetch("/api/sites");
    expect(events).toEqual(["invalid"]);

    vi.unstubAllGlobals();
  });
});
