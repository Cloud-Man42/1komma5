import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchAdminUsers, fetchAuthAudit } from "./adminUsersApi";

vi.mock("@/lib/auth", () => ({
  authFetch: vi.fn(),
}));

import { authFetch } from "@/lib/auth";

describe("adminUsersApi", () => {
  beforeEach(() => {
    vi.mocked(authFetch).mockReset();
  });

  it("fetchAdminUsers parses user list", async () => {
    vi.mocked(authFetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        users: [{ id: 1, username: "admin", email: "a@example.com", roles: [], sites: [] }],
      }),
    } as Response);

    const users = await fetchAdminUsers();
    expect(users).toHaveLength(1);
    expect(users[0].username).toBe("admin");
  });

  it("fetchAdminUsers throws on error response", async () => {
    vi.mocked(authFetch).mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: "Forbidden" }),
    } as Response);

    await expect(fetchAdminUsers()).rejects.toThrow("Forbidden");
  });

  it("fetchAuthAudit builds query string", async () => {
    vi.mocked(authFetch).mockResolvedValue({
      ok: true,
      json: async () => ({ events: [] }),
    } as Response);

    await fetchAuthAudit({ limit: 50, user_id: 2, success: false, event_type: "LOGIN" });
    expect(authFetch).toHaveBeenCalledWith("/api/admin/auth-audit?limit=50&user_id=2&event_type=LOGIN&success=false");
  });
});
