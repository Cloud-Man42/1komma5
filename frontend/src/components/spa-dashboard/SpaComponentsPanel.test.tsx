import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SpaStatus } from "@/lib/api";
import { SpaComponentsPanel } from "./SpaComponentsPanel";

function status(partial: Partial<SpaStatus> = {}): SpaStatus {
  return {
    consumer_id: 1,
    site_slug: "akarp",
    online: true,
    water_temperature_c: 37.8,
    set_temperature_c: 38,
    heater_active: true,
    pump_label: "Pump 1: High",
      filter_status: "Filtering",
      filter_cycle_active: true,
    errors: [],
    current_power_w: 2450,
    power_breakdown: { heater: 2000, pump1: 2100, pump2: 250, circulation: 100 },
    power_note_sv: "",
    last_updated: "2026-08-27T08:00:00Z",
    data_source: "ARCTIC_SPA_REST",
    data_quality: "CALCULATED",
    integration_enabled: true,
    ...partial,
  };
}

describe("SpaComponentsPanel", () => {
  it("renders component cards and framed tub image", () => {
    render(<SpaComponentsPanel status={status()} />);

    expect(screen.getByText("KOMPONENTER")).toBeInTheDocument();
    expect(screen.getByLabelText("Pumpar")).toBeInTheDocument();
    expect(screen.getByLabelText("Utrustning")).toBeInTheDocument();
    expect(screen.getByText("Pump 1")).toBeInTheDocument();
    expect(screen.getByText("Värmare")).toBeInTheDocument();
    expect(document.querySelector(".sdash-tub-frame")).toBeTruthy();
    expect(document.querySelector(".sdash-component-card")).toBeTruthy();
  });
});
