import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ArcticSpaPanel } from "@/components/ArcticSpaPanel";

const mockFetchSpaStatus = vi.fn();
const mockFetchSpaEnergyPeriod = vi.fn();
const mockFetchSpaHealth = vi.fn();
const mockFetchSpaHistory = vi.fn();
const mockFetchSpaEnergyBreakdown = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSpaStatus: (...args: unknown[]) => mockFetchSpaStatus(...args),
    fetchSpaEnergyPeriod: (...args: unknown[]) => mockFetchSpaEnergyPeriod(...args),
    fetchSpaHealth: (...args: unknown[]) => mockFetchSpaHealth(...args),
    fetchSpaHistory: (...args: unknown[]) => mockFetchSpaHistory(...args),
    fetchSpaEnergyBreakdown: (...args: unknown[]) => mockFetchSpaEnergyBreakdown(...args),
  };
});

describe("ArcticSpaPanel", () => {
  beforeEach(() => {
    mockFetchSpaStatus.mockReset();
    mockFetchSpaEnergyPeriod.mockReset();
    mockFetchSpaHealth.mockReset();
    mockFetchSpaHistory.mockReset();
    mockFetchSpaEnergyBreakdown.mockReset();
    mockFetchSpaStatus.mockResolvedValue({
      consumer_id: 1,
      site_slug: "akarp",
      online: true,
      water_temperature_c: 38.1,
      set_temperature_c: 39,
      heater_active: true,
      pump_label: "Pump 1: Low",
      filter_status: "Filtering",
      errors: [],
      current_power_w: 3200,
      last_updated: "2026-08-21T12:00:00Z",
      data_source: "ARCTIC_SPA_REST",
      data_quality: "CALCULATED",
      integration_enabled: true,
    });
    mockFetchSpaEnergyPeriod.mockResolvedValue({
      period: "today",
      energy_kwh: 0,
      actual_cost_sek: 0,
      has_data: false,
    });
    mockFetchSpaHealth.mockResolvedValue({
      consumer_id: 1,
      api_status: "DISABLED",
      spa_status: "OFFLINE",
      polling_status: "IDLE",
      database_status: "OK",
      samples_last_24h: 0,
      samples_with_power_24h: 0,
      sample_energy_kwh_24h: 0,
      intervals_last_24h: 0,
      data_quality: "MISSING",
    });
    mockFetchSpaHistory.mockResolvedValue({ period: "today", points: [] });
    mockFetchSpaEnergyBreakdown.mockResolvedValue({
      period: "today",
      granularity: "day",
      rows: [],
      total: { has_data: false, energy_kwh: 0, solar_kwh: 0, battery_kwh: 0, grid_kwh: 0, grid_cost_sek: 0, solar_value_sek: 0, battery_value_sek: 0 },
    });
  });

  it("shows waiting message when no energy data", async () => {
    render(<ArcticSpaPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByTestId("arctic-spa-panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Förbrukning idag")).toBeInTheDocument();
    expect(screen.getAllByText(/Väntar på mätdata/).length).toBeGreaterThan(0);
  });

  it("shows disabled message when integration off", async () => {
    mockFetchSpaStatus.mockResolvedValueOnce({
      integration_enabled: false,
    });
    render(<ArcticSpaPanel siteSlug="akarp" />);
    await waitFor(() => {
      expect(screen.getByText(/inte aktiverad/i)).toBeInTheDocument();
    });
  });
});
