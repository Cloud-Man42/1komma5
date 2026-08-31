import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PiEconomyBars, PiGauge, economyAxisLabels, type EconomyDay } from "./PiCharts";

const DAYS: EconomyDay[] = [
  { day: 1, savings_sek: 300, cost_sek: 150, net_sek: 150 },
  { day: 2, savings_sek: 100, cost_sek: 200, net_sek: -100 },
];

function bars(container: HTMLElement) {
  return Array.from(container.querySelectorAll("rect")).map((rect) => ({
    fill: rect.getAttribute("fill"),
    y: Number(rect.getAttribute("y")),
    height: Number(rect.getAttribute("height")),
  }));
}

describe("PiEconomyBars", () => {
  it("draws savings above the axis and cost below it", () => {
    const { container } = render(<PiEconomyBars daily={DAYS} />);
    const drawn = bars(container);
    const savings = drawn.filter((bar) => bar.fill === "#21cc3e");
    const cost = drawn.filter((bar) => bar.fill === "#ab37c3");

    expect(savings).toHaveLength(2);
    expect(cost).toHaveLength(2);
    for (const bar of savings) expect(bar.y).toBeLessThan(50);
    for (const bar of cost) expect(bar.y).toBe(50);
  });

  it("keeps cost below the axis even when the API reports it as a negative number", () => {
    const { container } = render(
      <PiEconomyBars daily={[{ day: 1, savings_sek: 300, cost_sek: -150, net_sek: 450 }]} />,
    );
    const cost = bars(container).filter((bar) => bar.fill === "#ab37c3");
    expect(cost).toHaveLength(1);
    expect(cost[0].y).toBe(50);
  });

  it("plots net on the side matching its own sign", () => {
    const { container } = render(<PiEconomyBars daily={DAYS} />);
    const net = bars(container).filter((bar) => bar.fill === "#3aa0e8");
    expect(net[0].y).toBeLessThan(50);
    expect(net[1].y).toBe(50);
  });

  it("scales the axis to a readable step above the data peak", () => {
    render(<PiEconomyBars daily={DAYS} />);
    expect(screen.getByText("300")).toBeInTheDocument();
    expect(screen.getByText("\u2212300")).toBeInTheDocument();
  });

  it("shows an empty state instead of an axis when there are no days", () => {
    render(<PiEconomyBars daily={[]} />);
    expect(screen.getByText("Data saknas")).toBeInTheDocument();
  });
});

describe("economyAxisLabels", () => {
  it("labels the first, quarter and last day of the month", () => {
    const days = Array.from({ length: 28 }, (_, index) => ({
      day: index + 1,
      savings_sek: 0,
      cost_sek: 0,
      net_sek: 0,
    }));
    expect(economyAxisLabels(days, 7)).toEqual(["1/8", "8/8", "15/8", "21/8", "28/8"]);
  });

  it("returns nothing for an empty month", () => {
    expect(economyAxisLabels([], 7)).toEqual([]);
  });
});

describe("PiGauge", () => {
  it("draws the groove, the full range and the surplus arc", () => {
    const { container } = render(<PiGauge fraction={0.45} />);
    const strokes = Array.from(container.querySelectorAll("circle")).map((circle) =>
      circle.getAttribute("stroke"),
    );
    expect(strokes).toEqual(["#2d3947", "#21cc3e", "#f9b208"]);
  });

  it("draws only the groove when there is no value, so the ring keeps its footprint", () => {
    const { container } = render(<PiGauge fraction={null} />);
    const strokes = Array.from(container.querySelectorAll("circle")).map((circle) =>
      circle.getAttribute("stroke"),
    );
    expect(strokes).toEqual(["#2d3947"]);
  });

  it("omits the surplus arc at zero rather than drawing a stub", () => {
    const { container } = render(<PiGauge fraction={0} />);
    const strokes = Array.from(container.querySelectorAll("circle")).map((circle) =>
      circle.getAttribute("stroke"),
    );
    expect(strokes).toEqual(["#2d3947", "#21cc3e"]);
  });

  it("clamps an out-of-range fraction to the full sweep", () => {
    const { container } = render(<PiGauge fraction={4} />);
    const circles = container.querySelectorAll("circle");
    const green = circles[1].getAttribute("stroke-dasharray");
    const amber = circles[2].getAttribute("stroke-dasharray");
    expect(amber).toBe(green);
  });
});
