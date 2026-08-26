import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalogBoostGauge } from "@/components/AnalogBoostGauge";

describe("AnalogBoostGauge", () => {
  it("renders label and kW readout", () => {
    render(
      <AnalogBoostGauge
        label="Solenergi"
        watts={3200}
        accent="#f59e0b"
        directionLabel="Produktion"
      />,
    );
    expect(screen.getByText("Solenergi")).toBeInTheDocument();
    expect(screen.getByText("3.20 kW")).toBeInTheDocument();
    expect(screen.getByText("Produktion")).toBeInTheDocument();
  });

  it("exposes meter semantics", () => {
    render(
      <AnalogBoostGauge
        label="Batteri"
        watts={-1500}
        mode="bidirectional"
        accent="#34d399"
      />,
    );
    expect(screen.getByRole("meter", { name: "Batteri" })).toHaveAttribute("aria-valuenow", "-1500");
  });
});
