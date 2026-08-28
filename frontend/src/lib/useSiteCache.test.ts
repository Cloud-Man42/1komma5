import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useSiteCache, clearSiteCache } from "@/lib/useSiteCache";

describe("useSiteCache", () => {
  beforeEach(() => {
    clearSiteCache("site:");
  });

  it("caches successful loads within TTL", async () => {
    const loader = vi.fn().mockResolvedValue({ ok: true });
    const { result, rerender } = renderHook(
      ({ key }) => useSiteCache(key, loader, 60_000),
      { initialProps: { key: "site:akarp:snapshot" } },
    );
    await waitFor(() => expect(result.current.data).toEqual({ ok: true }));
    expect(loader).toHaveBeenCalledTimes(1);
    rerender({ key: "site:akarp:snapshot" });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(loader).toHaveBeenCalledTimes(1);
  });

  it("surfaces loader errors", async () => {
    const loader = vi.fn().mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useSiteCache("site:err", loader, 1000));
    await waitFor(() => expect(result.current.error).toBe("network"));
  });
});
