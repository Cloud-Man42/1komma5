import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MOCKUP_NOW, MOCKUP_OVERVIEW } from "./__fixtures__/mockupOverview";
import { PiDetailView } from "./PiDetailView";
import { PI_SECTIONS, PI_SECTION_META } from "./piSections";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ back: vi.fn() }),
}));

describe("PiDetailView", () => {
  for (const section of PI_SECTIONS) {
    it(`shows Home and the ${section} title`, () => {
      render(
        <PiDetailView
          slug="preview"
          section={section}
          data={MOCKUP_OVERVIEW}
          connection="CONNECTED"
          error={null}
          nowOverride={MOCKUP_NOW}
        />,
      );
      expect(screen.getByRole("link", { name: "Hem" })).toHaveAttribute("href", "/display/preview");
      expect(screen.getByRole("heading", { level: 1, name: PI_SECTION_META[section].title })).toBeTruthy();
    });
  }

  it("gives the flow diagram a uniform scale, since its box is far wider here", () => {
    const { container } = render(
      <PiDetailView
        slug="preview"
        section="grid"
        data={MOCKUP_OVERVIEW}
        connection="CONNECTED"
        error={null}
        nowOverride={MOCKUP_NOW}
      />,
    );

    expect(container.querySelector(".pi-flow-svg")?.getAttribute("preserveAspectRatio")).toBe(
      "xMidYMid meet",
    );
  });

  it("marks the section on the layout root so it can be shaped per section", () => {
    const { container } = render(
      <PiDetailView
        slug="preview"
        section="grid"
        data={MOCKUP_OVERVIEW}
        connection="CONNECTED"
        error={null}
        nowOverride={MOCKUP_NOW}
      />,
    );

    expect(container.querySelector(".pi-detail")?.className).toContain("pi-detail-section-grid");
  });

  it("keeps both the diagram and the grid sparkline in the flow section", () => {
    const { container } = render(
      <PiDetailView
        slug="preview"
        section="grid"
        data={MOCKUP_OVERVIEW}
        connection="CONNECTED"
        error={null}
        nowOverride={MOCKUP_NOW}
      />,
    );

    expect(container.querySelector(".pi-flow-svg")).not.toBeNull();
    expect(container.querySelector(".pi-detail-chart-inline")).not.toBeNull();
    expect(screen.getByText("Netto mot nät")).toBeTruthy();
  });

  it("shows placeholders instead of fabricated zeros when data is missing", () => {
    render(
      <PiDetailView
        slug="preview"
        section="battery"
        data={null}
        connection="OFFLINE"
        error="offline"
        nowOverride={MOCKUP_NOW}
      />,
    );
    expect(screen.getAllByText("--").length).toBeGreaterThan(0);
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("does not render a back button without browser history", () => {
    render(
      <PiDetailView
        slug="preview"
        section="solar"
        data={MOCKUP_OVERVIEW}
        connection="CONNECTED"
        error={null}
        nowOverride={MOCKUP_NOW}
      />,
    );
    expect(screen.queryByRole("button", { name: /tillbaka/i })).not.toBeInTheDocument();
  });
});
