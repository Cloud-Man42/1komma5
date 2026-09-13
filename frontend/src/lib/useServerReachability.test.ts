import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useServerReachability } from "@/lib/useServerReachability";

vi.mock("@/lib/useOnlineStatus", () => ({
  useOnlineStatus: () => false,
}));

describe("useServerReachability", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("reports offline without probing when browser is offline", async () => {
    const { result } = renderHook(() => useServerReachability());
    await waitFor(() => {
      expect(result.current.status).toBe("offline");
    });
    expect(fetch).not.toHaveBeenCalled();
  });
});
