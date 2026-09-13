import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchMultiSiteOverview, fetchSiteSelection } from "./multiSiteApi";

vi.mock("@/lib/auth", () => ({ authFetch: vi.fn() }));

import { authFetch } from "@/lib/auth";

describe("multiSiteApi", () => {
  beforeEach(() => {
    vi.mocked(authFetch).mockReset();
  });

  it("fetchMultiSiteOverview posts slugs", async () => {
    vi.mocked(authFetch).mockResolvedValue({
      ok: true,
      json: async () => ({ sites: [], aggregate: {} }),
    } as Response);

    await fetchMultiSiteOverview(["akarp", "summer-house-denmark"]);
    expect(authFetch).toHaveBeenCalledWith(
      "/api/multi-site/overview",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ site_slugs: ["akarp", "summer-house-denmark"] }),
      }),
    );
  });

  it("fetchSiteSelection throws on error", async () => {
    vi.mocked(authFetch).mockResolvedValue({ ok: false, status: 403 } as Response);
    await expect(fetchSiteSelection()).rejects.toThrow("403");
  });
});
