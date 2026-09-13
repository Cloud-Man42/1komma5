import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OfflineRecovery } from "@/components/pwa/OfflineRecovery";

const replace = vi.fn();

vi.mock("@/lib/useOnlineStatus", () => ({
  useOnlineStatus: () => true,
}));

describe("OfflineRecovery", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.stubGlobal("location", { ...window.location, replace });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );
  });

  it("shows unreachable guidance when health probe fails", async () => {
    render(<OfflineRecovery />);
    expect(await screen.findByText(/EMIC svarar inte/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Försök igen/i })).toBeInTheDocument();
  });

  it("redirects to /app when server is reachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200 }),
    );
    render(<OfflineRecovery />);
    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/app");
    });
  });

  it("retries health probe when user clicks retry", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    vi.stubGlobal("fetch", fetchMock);
    render(<OfflineRecovery />);
    await screen.findByText(/EMIC svarar inte/i);
    fireEvent.click(screen.getByRole("button", { name: /Försök igen/i }));
    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });
});
