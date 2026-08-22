import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  DashboardSection,
  EmptyState,
  ErrorState,
  Metric,
  StatusBadge,
} from "@/components/dashboard";

describe("dashboard primitives", () => {
  it("renders DashboardSection with title", () => {
    render(
      <DashboardSection title="Idag">
        <p>Innehåll</p>
      </DashboardSection>,
    );
    expect(screen.getByRole("heading", { name: "Idag" })).toBeTruthy();
    expect(screen.getByText("Innehåll")).toBeTruthy();
  });

  it("renders Metric with label and value", () => {
    render(<Metric label="Producerat" value="31,8 kWh" />);
    expect(screen.getByText("Producerat")).toBeTruthy();
    expect(screen.getByText("31,8 kWh")).toBeTruthy();
  });

  it("renders StatusBadge with label", () => {
    render(<StatusBadge label="Allt normalt" tone="success" />);
    expect(screen.getByRole("status").textContent).toContain("Allt normalt");
  });

  it("renders EmptyState", () => {
    render(<EmptyState title="Ingen laddbox" text="Anslut en laddare" />);
    expect(screen.getByText("Ingen laddbox")).toBeTruthy();
  });

  it("renders ErrorState as alert", () => {
    render(<ErrorState title="Prognos otillgänglig" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Prognos otillgänglig");
  });
});
