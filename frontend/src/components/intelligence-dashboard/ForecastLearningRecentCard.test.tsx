import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ForecastLearningRecentCard } from "./ForecastLearningRecentCard";
import type { ForecastLearningRecent } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchForecastLearningRecent: vi.fn(),
}));

import { fetchForecastLearningRecent } from "@/lib/api";

const sample: ForecastLearningRecent = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  kind: null,
  snapshots: [
    {
      kind: "solar_w",
      predicted_value: 1200,
      actual_value: 1100,
      forecast_recorded_at: "2026-09-04T08:00:00Z",
      actual_recorded_at: "2026-09-04T09:00:00Z",
      model_version: "v1",
    },
  ],
};

describe("ForecastLearningRecentCard", () => {
  it("shows empty state", async () => {
    vi.mocked(fetchForecastLearningRecent).mockResolvedValue({
      slug: "akarp",
      timezone: "Europe/Stockholm",
      kind: null,
      snapshots: [],
    });
    render(<ForecastLearningRecentCard slug="akarp" timezone="Europe/Stockholm" />);
    await waitFor(() => {
      expect(screen.getByText(/Inga avslutade prognosperioder/)).toBeInTheDocument();
    });
  });

  it("renders recent snapshots", async () => {
    vi.mocked(fetchForecastLearningRecent).mockResolvedValue(sample);
    render(<ForecastLearningRecentCard slug="akarp" timezone="Europe/Stockholm" />);
    await waitFor(() => {
      expect(screen.getByText("solar_w")).toBeInTheDocument();
      expect(screen.getByText(/utfall 1100/)).toBeInTheDocument();
    });
  });

  it("shows error on failure", async () => {
    vi.mocked(fetchForecastLearningRecent).mockRejectedValue(new Error("503"));
    render(<ForecastLearningRecentCard slug="akarp" timezone="Europe/Stockholm" />);
    await waitFor(() => {
      expect(screen.getByText(/Kunde inte hämta prognosjämförelser/)).toBeInTheDocument();
    });
  });
});
