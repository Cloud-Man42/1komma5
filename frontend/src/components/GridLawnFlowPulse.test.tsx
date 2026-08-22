import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { GridLawnFlowPulse } from "./GridLawnFlowPulse";

describe("GridLawnFlowPulse", () => {
  it("renders fixed direction arrows along the lawn cable", () => {
    render(
      <svg viewBox="0 0 100 67">
        <GridLawnFlowPulse path="M 53 63.5 L 51.17 34.31" watts={1200} mode="import" />
      </svg>,
    );
    expect(document.querySelector(".energy-grid-lawn-flow-track")).toBeTruthy();
    expect(document.querySelector(".energy-grid-lawn-flow-import")).toBeTruthy();
    expect(document.querySelector(".energy-grid-lawn-flow-direction")).toBeTruthy();
    expect(document.querySelectorAll(".energy-grid-lawn-flow-arrow").length).toBe(8);
    expect(document.querySelectorAll(".energy-grid-lawn-flow-arrow-glow").length).toBe(8);
    expect(document.querySelectorAll(".energy-grid-lawn-flow-arrow-core").length).toBe(8);
    expect(document.querySelector(".energy-grid-lawn-flow-stream")).toBeNull();
    expect(document.querySelector(".energy-grid-lawn-flow-pulse")).toBeNull();
  });

  it("uses export styling for grid export", () => {
    render(
      <svg viewBox="0 0 100 67">
        <GridLawnFlowPulse path="M 51.17 34.31 L 53 63.5" watts={900} mode="export" />
      </svg>,
    );
    expect(document.querySelector(".energy-grid-lawn-flow-export")).toBeTruthy();
  });

  it("renders nothing when flow is below threshold", () => {
    render(
      <svg viewBox="0 0 100 67">
        <GridLawnFlowPulse path="M 53 63.5 L 51.17 34.31" watts={5} mode="import" />
      </svg>,
    );
    expect(document.querySelector(".energy-grid-lawn-flow-track")).toBeNull();
  });
});
