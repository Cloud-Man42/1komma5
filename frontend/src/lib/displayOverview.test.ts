import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDisplayOverview } from "./displayOverview";

function mockFetch(response: Partial<Response>): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue(response as Response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("fetchDisplayOverview", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps the request same-origin so the proxy header or the cookie applies", async () => {
    const fetchMock = mockFetch({
      ok: true,
      status: 200,
      json: async () => ({ site: { slug: "akarp" } }),
    });

    await fetchDisplayOverview("akarp");

    const [url, init] = fetchMock.mock.calls[0];
    // A relative URL is what makes the enrolled cookie travel with the request.
    expect(url).toBe("/api/v1/display/overview/akarp");
    expect(init).toMatchObject({ cache: "no-store", credentials: "same-origin" });
  });

  it("returns the parsed payload", async () => {
    mockFetch({
      ok: true,
      status: 200,
      json: async () => ({ site: { slug: "akarp", name: "Åkarp" } }),
    });

    const overview = await fetchDisplayOverview("akarp");

    expect(overview.site.name).toBe("Åkarp");
  });

  it("reports the status when the browser is not enrolled", async () => {
    mockFetch({ ok: false, status: 401, json: async () => ({}) });

    await expect(fetchDisplayOverview("akarp")).rejects.toThrow("401");
  });

  it("reports the status when the site is unknown", async () => {
    mockFetch({ ok: false, status: 404, json: async () => ({}) });

    await expect(fetchDisplayOverview("nowhere")).rejects.toThrow("Display overview failed: 404");
  });
});
