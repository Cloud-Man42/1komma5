import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ForecastLearningCard } from "./ForecastLearningCard";
import type { ForecastLearningSummary } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchForecastLearningSummary: vi.fn(),
}));

import { fetchForecastLearningSummary } from "@/lib/api";

const emptySummary: ForecastLearningSummary = {
  slug: "akarp",
  timezone: "Europe/Stockholm",
  days: 30,
  metrics: [
    { kind: "import_price_sek_kwh", mae: null, bias: null, sample_count: 0, mape_pct: null },
    { kind: "load_w", mae: null, bias: null, sample_count: 0, mape_pct: null },
    { kind: "solar_w", mae: null, bias: null, sample_count: 0, mape_pct: null },
  ],
  last_reconciled_at: null,
};

const withData: ForecastLearningSummary = {
  ...emptySummary,
  metrics: [
    { kind: "import_price_sek_kwh", mae: 0.012, bias: -0.005, sample_count: 42, mape_pct: 1.2 },
    { kind: "load_w", mae: 350, bias: 120, sample_count: 38, mape_pct: null },
    { kind: "solar_w", mae: 280, bias: -50, sample_count: 30, mape_pct: 8.5 },
  ],
  last_reconciled_at: "2026-09-02T10:00:00Z",
};

describe("ForecastLearningCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no samples", async () => {
    vi.mocked(fetchForecastLearningSummary).mockResolvedValue(emptySummary);
    render(<ForecastLearningCard slug="akarp" />);
    expect(await screen.findByText(/Samlar in prognoser/)).toBeInTheDocument();
  });

  it("shows metrics when samples exist", async () => {
    vi.mocked(fetchForecastLearningSummary).mockResolvedValue(withData);
    render(<ForecastLearningCard slug="akarp" />);
    expect(await screen.findByText("Elpris (inköp)")).toBeInTheDocument();
    expect(screen.getByText("Hushållslast")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("shows error state on fetch failure", async () => {
    vi.mocked(fetchForecastLearningSummary).mockRejectedValue(new Error("503"));
    render(<ForecastLearningCard slug="akarp" />);
    expect(await screen.findByText(/Kunde inte hämta prognosdata/)).toBeInTheDocument();
  });
});
