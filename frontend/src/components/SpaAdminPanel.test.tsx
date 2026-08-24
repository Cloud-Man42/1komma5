import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SpaAdminPanel } from "@/components/SpaAdminPanel";

const mockFetchSpaConfig = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchSpaConfig: (...args: unknown[]) => mockFetchSpaConfig(...args),
  updateSpaConfig: vi.fn(),
  testSpaConnection: vi.fn(),
}));

describe("SpaAdminPanel", () => {
  beforeEach(() => {
    mockFetchSpaConfig.mockReset();
    mockFetchSpaConfig.mockResolvedValue({
      integration_enabled: false,
      api_base_url: "https://api.myarcticspa.com",
      masked_api_key: "",
      external_spa_id: "",
      poll_interval_seconds: 60,
      energy_collection_enabled: true,
      cost_calculation_enabled: true,
    });
  });

  it("shows Arctic Spa title without duplicate Integrations prefix", async () => {
    render(<SpaAdminPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("spa-admin-panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Arctic Spa")).toBeInTheDocument();
    expect(screen.queryByText(/Integrations → Arctic Spa/)).not.toBeInTheDocument();
  });
});
