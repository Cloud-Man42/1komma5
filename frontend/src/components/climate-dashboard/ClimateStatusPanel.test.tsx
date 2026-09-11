import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClimateStatusPanel } from "./ClimateStatusPanel";

vi.mock("@/lib/adminAuth", () => ({ getAdminToken: () => "token" }));

describe("ClimateStatusPanel", () => {
  it("shows empty state when no devices", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ devices: [] }),
      }),
    );
    render(<ClimateStatusPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("climate-empty")).toBeInTheDocument();
  });

  it("renders device cards", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          devices: [
            {
              device_id: "pod1",
              display_name: "Office",
              temperature_c: 21.5,
              humidity_percent: 40,
              online: true,
              observed_at: "2026-09-09T10:00:00Z",
            },
          ],
        }),
      }),
    );
    render(<ClimateStatusPanel siteSlug="akarp" />);
    expect(await screen.findByTestId("climate-device-pod1")).toBeInTheDocument();
    expect(screen.getByText(/21.5/)).toBeInTheDocument();
  });
});
