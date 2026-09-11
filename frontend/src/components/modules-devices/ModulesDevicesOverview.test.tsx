import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ModulesDevicesOverview } from "@/components/modules-devices/ModulesDevicesOverview";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("site=akarp"),
  usePathname: () => "/config/modules-devices",
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSites: vi.fn().mockResolvedValue([
      {
        slug: "akarp",
        name: "Åkarp",
        timezone: "Europe/Stockholm",
        fallback_purchase_price_sek_kwh: 1,
        export_compensation_sek_kwh: 0,
        latest_reading: null,
      },
      {
        slug: "denmark",
        name: "Danmark",
        timezone: "Europe/Copenhagen",
        fallback_purchase_price_sek_kwh: 1,
        export_compensation_sek_kwh: 0,
        latest_reading: null,
      },
    ]),
    fetchSiteOperations: vi.fn().mockResolvedValue({
      slug: "akarp",
      overall_health_status: "healthy",
      modules: [],
      devices: [],
      integration_health: [],
    }),
  };
});

describe("ModulesDevicesOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads sites dynamically", async () => {
    render(<ModulesDevicesOverview />);
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Åkarp" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Danmark" })).toBeInTheDocument();
    });
  });
});
