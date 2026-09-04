import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SiteDashboard } from "@/lib/api";
import { PeakProtectionCard } from "./PeakProtectionCard";

const baseDashboard = {
  alerts: [{ severity: "info", message_sv: "Normal produktion" }],
} as SiteDashboard;

describe("PeakProtectionCard", () => {
  it("shows calm state when no peak alerts", () => {
    render(<PeakProtectionCard dashboard={baseDashboard} />);
    expect(screen.getByText(/Ingen aktiv effekttoppsvarning/)).toBeInTheDocument();
  });

  it("lists effekttariff alerts", () => {
    render(
      <PeakProtectionCard
        dashboard={{
          ...baseDashboard,
          alerts: [{ severity: "warning", message_sv: "Import nära säkringsgräns (effekttariff)" }],
        }}
      />,
    );
    expect(screen.getByText(/Import nära säkringsgräns/)).toBeInTheDocument();
  });
});
